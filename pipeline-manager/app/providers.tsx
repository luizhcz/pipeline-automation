"use client"

import type React from "react"

import { PipelineStoreProvider } from "@/context/pipeline-store"

export function Providers({ children }: { children: React.ReactNode }) {
  return <PipelineStoreProvider>{children}</PipelineStoreProvider>
}
