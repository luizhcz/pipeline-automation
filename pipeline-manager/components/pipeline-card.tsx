"use client"

import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import type { Pipeline } from "@/types/pipeline"
import { formatDate } from "@/lib/utils"

interface PipelineCardProps {
  pipeline: Pipeline
  onClick: () => void
}

export default function PipelineCard({ pipeline, onClick }: PipelineCardProps) {
  return (
    <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={onClick}>
      <CardHeader>
        <CardTitle className="truncate">{pipeline.name}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-muted-foreground line-clamp-2">{pipeline.description || "Sem descrição"}</p>
      </CardContent>
      <CardFooter className="flex justify-between text-xs text-muted-foreground">
        <span>{pipeline.parameters.length} parâmetros</span>
        <span>Criado em {formatDate(pipeline.created_at)}</span>
      </CardFooter>
    </Card>
  )
}
