import type { Metadata } from "next";
import { GeistSans } from "geist/font";
import { GeistMono } from "geist/font/mono";
import "./globals.css";
import { AppShell } from "../components/app-shell";
import { Providers } from "../components/providers";

export const metadata: Metadata = {
  title: { default: "Agent Quality Benchmark", template: "%s · AQB" },
  description: "Evidence-first, reproducible quality benchmarks for AI agents.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${GeistSans.variable} ${GeistMono.variable}`}>
        <Providers><AppShell>{children}</AppShell></Providers>
      </body>
    </html>
  );
}
