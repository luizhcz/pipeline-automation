"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { usePipelineStore } from "@/context/pipeline-store"
import PipelineSelector from "@/components/pipeline-selector"
import ExecutionForm from "@/components/execution-form"
import type { ExecutionResult } from "@/types/pipeline"
import { useToast } from "@/components/ui/use-toast"

export default function ExecutePipeline() {
  const { pipelines } = usePipelineStore()
  const { toast } = useToast()
  const [selectedPipelineId, setSelectedPipelineId] = useState<string | null>(null)

  const selectedPipeline = selectedPipelineId
    ? pipelines.find((p) => p.id === selectedPipelineId)
    : null

    const handleExecutePipeline = async (
      parameters: Record<string, any>
    ): Promise<ExecutionResult> => {
      if (!selectedPipeline) {
        return {
          success: false,
          message: "Nenhum pipeline selecionado.",
        }
      }
    
      const payload = {
        tasks: [
          {
            notebook_name: selectedPipeline.name,
            version: "1",
            params: parameters,
          },
        ],
      }
    
      try {
        const response = await fetch("http://localhost:8000/submit", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        })
    
        const responseData = await response.json()
    
        if (!response.ok) {
          const errorMessage =
            responseData?.detail?.[0]?.msg ||
            "Erro desconhecido ao enviar pipeline."
    
          toast({
            variant: "destructive",
            title: "Erro na execução do pipeline",
            description: errorMessage,
          })
    
          return {
            success: false,
            message: errorMessage,
            logs: [
              `[ERROR] Falha na execução do pipeline "${selectedPipeline.name}"`,
              `[ERROR] Detalhes: ${errorMessage}`,
            ],
          }
        }
    
        toast({
          title: "Pipeline enviado com sucesso!",
          description: `Request IDs: ${responseData.request_ids.join(", ")}`,
        })
    
        return {
          success: true,
          message: "Pipeline enfileirado com sucesso",
          logs: [
            `[INFO] Pipeline "${selectedPipeline.name}" enviado para execução.`,
            `[INFO] Parâmetros: ${JSON.stringify(parameters, null, 2)}`,
            `[INFO] Request IDs: ${responseData.request_ids.join(", ")}`,
          ],
        }
      } catch (error: any) {
        toast({
          variant: "destructive",
          title: "Erro de rede ou exceção",
          description: error?.message || "Erro inesperado na execução",
        })
    
        return {
          success: false,
          message: "Erro inesperado na execução",
          logs: [
            `[ERROR] Exceção ao tentar enviar pipeline`,
            `[ERROR] ${error.message}`,
          ],
        }
      }
    }    

  return (
    <div className="container mx-auto">
      <h1 className="text-3xl font-bold mb-6">Executar Pipeline</h1>

      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Selecione um Pipeline</CardTitle>
          </CardHeader>
          <CardContent>
            {pipelines.length === 0 ? (
              <p className="text-muted-foreground">
                Você ainda não possui pipelines cadastrados. Crie um pipeline primeiro.
              </p>
            ) : (
              <PipelineSelector
                pipelines={pipelines}
                selectedPipelineId={selectedPipelineId}
                onSelect={setSelectedPipelineId}
              />
            )}
          </CardContent>
        </Card>

        {selectedPipeline && (
          <div className="mt-6">
            <h2 className="text-xl font-semibold mb-4">
              Configurar Execução: {selectedPipeline.name}
            </h2>
            {selectedPipeline.parameters.length === 0 ? (
              <Card>
                <CardContent className="p-6">
                  <p className="text-muted-foreground">
                    Este pipeline não possui parâmetros para configurar.
                  </p>
                </CardContent>
              </Card>
            ) : (
              <ExecutionForm
                pipeline={selectedPipeline}
                onExecute={handleExecutePipeline}
              />
            )}
          </div>
        )}
      </div>
    </div>
  )
}