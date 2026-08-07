import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "AgentBruce — Cyberforensics Intelligence Center",
  description:
    "Agentic Cyberforensics Investigation Operating System. Real-time case management, intelligence graph exploration, and multi-agent forensic analysis.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="light" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased bg-[#f4f6fb]`} suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}