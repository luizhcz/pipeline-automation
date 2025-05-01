"use client"

import { useEffect, useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { usePipelineStore } from "@/context/pipeline-store"
import PipelineCard from "@/components/pipeline-card"
import EditPipelineModal from "@/components/edit-pipeline-modal"
import type { Pipeline } from "@/types/pipeline"

export default function MyPipelines() {
  const { pipelines, setPipelines } = usePipelineStore()
  const [selectedPipeline, setSelectedPipeline] = useState<Pipeline | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  useEffect(() => {
    const fetchPipelines = async () => {
      try {
        const response = await fetch("http://localhost:8000/pipelines")
        if (!response.ok) throw new Error("Erro ao buscar pipelines")

        const data = await response.json()

        const mappedPipelines: Pipeline[] = data.map((item: any) => ({
          id: item.id,
          name: item.name,
          description: item.description,
          createdAt: new Date(item.created_at),
          parameters: item.parameters.map((param: any) => ({
            key: param.name,
            type: param.type,
            value: param.value ?? null,
          })),
        }))

        setPipelines(mappedPipelines)
      } catch (error) {
        console.error("Erro ao buscar pipelines:", error)
      }
    }

    fetchPipelines()
  }, [setPipelines])

  const handlePipelineClick = (pipeline: Pipeline) => {
    setSelectedPipeline(pipeline)
    setIsModalOpen(true)
  }

  const closeModal = () => {
    setIsModalOpen(false)
    setSelectedPipeline(null)
  }

  return (
    <div className="container mx-auto">
      <h1 className="text-3xl font-bold mb-6">Meus Pipelines</h1>

      {pipelines.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center p-6">
            <p className="text-muted-foreground text-center">Você ainda não possui pipelines cadastrados.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {pipelines.map((pipeline) => (
            <PipelineCard key={pipeline.id} pipeline={pipeline} onClick={() => handlePipelineClick(pipeline)} />
          ))}
        </div>
      )}

      {selectedPipeline && (
        <EditPipelineModal pipeline={selectedPipeline} isOpen={isModalOpen} onClose={closeModal} />
      )}
    </div>
  )
}