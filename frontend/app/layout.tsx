import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Rate Tracker Dashboard",
  description: "Real-time financial rate tracking and analysis dashboard",
  viewport: "width=device-width, initial-scale=1",
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
