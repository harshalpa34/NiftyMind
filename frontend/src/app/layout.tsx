import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NiftyMind - GenAI Assistant",
  description: "A modern GenAI application",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
