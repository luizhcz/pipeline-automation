"use client"

import type React from "react"
import { createContext, useContext, useEffect, useState } from "react"
import type { Pipeline } from "@/types/pipeline"

interface PipelineStoreContextType {
  pipelines: Pipeline[]
  addPipeline: (pipeline: Pipeline) => void
  updatePipeline: (pipeline: Pipeline) => void
  deletePipeline: (id: string) => void
  setPipelines: (pipelines: Pipeline[]) => void
}

const PipelineStoreContext = createContext<PipelineStoreContextType | undefined>(undefined)

export function PipelineStoreProvider({ children }: { children: React.ReactNode }) {
  const [pipelines, setPipelinesState] = useState<Pipeline[]>([])

  // Load pipelines from localStorage on mount
  useEffect(() => {
    const storedPipelines = localStorage.getItem("pipelines")
    if (storedPipelines) {
      try {
        const parsedPipelines = JSON.parse(storedPipelines)
        const pipelinesWithDates = parsedPipelines.map((pipeline: any) => ({
          ...pipeline,
          createdAt: new Date(pipeline.createdAt),
        }))
        setPipelinesState(pipelinesWithDates)
      } catch (error) {
        console.error("Error parsing stored pipelines:", error)
      }
    }
  }, [])

  // Save pipelines to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem("pipelines", JSON.stringify(pipelines))
  }, [pipelines])

  const addPipeline = (pipeline: Pipeline) => {
    setPipelinesState((prev) => [...prev, pipeline])
  }

  const updatePipeline = (updatedPipeline: Pipeline) => {
    setPipelinesState((prev) =>
      prev.map((pipeline) => (pipeline.id === updatedPipeline.id ? updatedPipeline : pipeline))
    )
  }

  const deletePipeline = (id: string) => {
    setPipelinesState((prev) => prev.filter((pipeline) => pipeline.id !== id))
  }

  const setPipelines = (newPipelines: Pipeline[]) => {
    setPipelinesState(newPipelines)
  }

  return (
    <PipelineStoreContext.Provider
      value={{ pipelines, addPipeline, updatePipeline, deletePipeline, setPipelines }}
    >
      {children}
    </PipelineStoreContext.Provider>
  )
}

export function usePipelineStore() {
  const context = useContext(PipelineStoreContext)
  if (context === undefined) {
    throw new Error("usePipelineStore must be used within a PipelineStoreProvider")
  }
  return context
}