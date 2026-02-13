import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { ErrorBoundary } from "@/components/ui/ErrorBoundary";
import { AuthGuard } from "@/components/auth";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Agent B Research - Local Research Workbench",
  description: "A packaged research workbench based on the original Agent B platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <ErrorBoundary>
          <Providers>
            <AuthGuard>{children}</AuthGuard>
          </Providers>
        </ErrorBoundary>
      </body>
    </html>
  );
}
