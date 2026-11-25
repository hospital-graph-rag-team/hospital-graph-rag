import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { ClinicalProvider } from "@/components/providers/clinical-provider";
import { AppShell } from "@/components/layout/app-shell";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "ClinicalGraph 2.0 — Hospital Graph RAG & Clinical Intelligence",
  description:
    "Interactive healthcare knowledge graph analytics, longitudinal biomarker tracking, and evidence-grounded Graph RAG platform.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`dark ${inter.variable} ${jetbrainsMono.variable}`}>
      <body className="font-sans antialiased">
        <ClinicalProvider>
          <AppShell>{children}</AppShell>
        </ClinicalProvider>
      </body>
    </html>
  );
}
