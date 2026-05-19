import asyncio
import json
import httpx
import websockets

BASE = "http://localhost:8000/api/v1"
WS_BASE = "ws://localhost:8000"


async def test_guardrail_websocket():
    """Test guardrail WebSocket alerts for behavioral flags"""
    
    print("\n" + "="*60)
    print("  GUARDRAIL WEBSOCKET TEST")
    print("="*60)
    
    # STEP 1 — Create session
    print("\n>>> STEP 1: Creating session...")
    r = httpx.post(f"{BASE}/sessions?user_id=test_trader")
    if r.status_code != 201:
        print(f"❌ Failed to create session: {r.text}")
        return
    
    session = r.json()
    session_id = session["session_id"]
    print(f"✅ Session created: {session_id}")
    
    # STEP 2 — Connect WebSocket
    print("\n>>> STEP 2: Connecting WebSocket...")
    try:
        async with websockets.connect(f"{WS_BASE}/ws/session/{session_id}") as ws:
            print(f"✅ WebSocket connected to session")
            
            # Receive CONNECTED message
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            connected_msg = json.loads(msg)
            print(f"   Received: {connected_msg['type']}")
            
            # STEP 3 — Trigger 3 consecutive losses
            print("\n>>> STEP 3: Opening and closing 3 trades at loss...")
            
            for i in range(1, 4):
                print(f"\n   Trade {i}:")
                
                # Open trade
                r = httpx.post(
                    f"{BASE}/sessions/{session_id}/trades",
                    json={
                        "symbol": "NIFTY",
                        "direction": "LONG",
                        "entry_price": 24500,
                        "quantity": 50,
                        "notes": f"Test trade {i}"
                    }
                )
                
                if r.status_code != 201:
                    print(f"   ❌ Failed to open trade: {r.text}")
                    return
                
                trade_data = r.json()
                open_trade_ids = trade_data.get("open_trade_ids", [])
                if not open_trade_ids:
                    print(f"   ❌ No trade_id in response")
                    return
                
                trade_id = open_trade_ids[-1]
                print(f"   ✅ Trade opened: {trade_id}")
                
                # Check for alert (on open)
                try:
                    alert_msg = await asyncio.wait_for(ws.recv(), timeout=2)
                    alert = json.loads(alert_msg)
                    if alert.get("type") == "GUARDRAIL_ALERT":
                        print(f"   ⚠️  Alert on open: {alert['flag_types']}")
                except asyncio.TimeoutError:
                    print(f"   (No alert on trade open)")
                
                # Close trade at loss
                r = httpx.post(
                    f"{BASE}/sessions/{session_id}/trades/close",
                    json={
                        "trade_id": trade_id,
                        "exit_price": 24300  # Loss
                    }
                )
                
                if r.status_code != 200:
                    print(f"   ❌ Failed to close trade: {r.text}")
                    return
                
                close_data = r.json()
                pnl = close_data.get("total_pnl", 0)
                consecutive_losses = close_data.get("consecutive_losses", 0)
                print(f"   ✅ Trade closed | PnL: {pnl} | Losses: {consecutive_losses}")
                
                # Wait for guardrail alert
                try:
                    alert_msg = await asyncio.wait_for(ws.recv(), timeout=2)
                    alert = json.loads(alert_msg)
                    
                    if alert.get("type") == "GUARDRAIL_ALERT":
                        print(f"   ⚠️  GUARDRAIL ALERT received!")
                        print(f"      Severity: {alert['severity']}")
                        print(f"      Flags: {alert['flag_types']}")
                        print(f"      Message: {alert['message'][:80]}...")
                        
                        # Verify alert content
                        if alert['severity'] == 'HIGH' and i == 3:
                            print(f"      ✅ HIGH severity detected on 3rd loss!")
                        if 'REVENGE_TRADE' in alert['flag_types'] and i == 3:
                            print(f"      ✅ REVENGE_TRADE flag detected!")
                    else:
                        print(f"   ℹ️  Received: {alert.get('type')}")
                
                except asyncio.TimeoutError:
                    print(f"   ⚠️  No alert received (timeout)")
                
                # Small delay between trades
                await asyncio.sleep(0.5)
            
            # STEP 4 — Verify final session state
            print("\n>>> STEP 4: Verifying final session state...")
            r = httpx.get(f"{BASE}/sessions/{session_id}")
            final_state = r.json()
            
            print(f"   Total Trades: {final_state['total_trades']}")
            print(f"   Total PnL: {final_state['total_pnl']}")
            print(f"   Consecutive Losses: {final_state['consecutive_losses']}")
            print(f"   Guardrail Active: {final_state['guardrail_active']}")
            
            flags = final_state.get("behavior_flags", [])
            print(f"   Behavior Flags: {len(flags)}")
            for flag in flags:
                print(f"     - {flag['flag_type']} ({flag['severity']})")
            
            # STEP 5 — Verification
            print("\n>>> STEP 5: Verification Results")
            checks = [
                ("total_trades == 3", final_state["total_trades"] == 3),
                ("consecutive_losses == 3", final_state["consecutive_losses"] == 3),
                ("total_pnl < 0", final_state["total_pnl"] < 0),
                ("guardrail_active == True", final_state["guardrail_active"] is True),
                ("REVENGE_TRADE flag present", any(
                    f["flag_type"] == "REVENGE_TRADE" for f in flags
                ))
            ]
            
            all_passed = True
            for check_name, passed in checks:
                emoji = "✅" if passed else "❌"
                print(f"   {emoji} {check_name}")
                if not passed:
                    all_passed = False
            
            if all_passed:
                print("\n🎉 All guardrail WebSocket tests passed!")
            else:
                print("\n⚠️  Some tests failed")
            
            # Send heartbeat
            print("\n>>> STEP 6: Testing heartbeat...")
            await ws.send("heartbeat")
            hb = await asyncio.wait_for(ws.recv(), timeout=2)
            hb_msg = json.loads(hb)
            if hb_msg.get("type") == "HEARTBEAT":
                print(f"   ✅ Heartbeat response received")
            else:
                print(f"   ❌ Unexpected response: {hb_msg}")
    
    except asyncio.TimeoutError:
        print("❌ WebSocket timeout")
    except websockets.exceptions.WebSocketException as e:
        print(f"❌ WebSocket error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("Starting Guardrail WebSocket Tests")
    print("Make sure the server is running: python main.py")
    print("=" * 60)
    
    asyncio.run(test_guardrail_websocket())
