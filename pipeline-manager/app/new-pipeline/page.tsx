"use client"

import type React from "react"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { useToast } from "@/components/ui/use-toast"
import { usePipelineStore } from "@/context/pipeline-store"
import ParametersTable from "@/components/parameters-table"
import { v4 as uuidv4 } from "uuid"
import type { Pipeline, PipelineParameter } from "@/types/pipeline"

export default function NewPipeline() {
  const router = useRouter()
  const { toast } = useToast()
  const { addPipeline } = usePipelineStore()

  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [parameters, setParameters] = useState<PipelineParameter[]>([])
  const [errors, setErrors] = useState<Record<string, string>>({})

  const resetForm = () => {
    setName("")
    setDescription("")
    setParameters([])
    setErrors({})
  }

  const validateForm = () => {
    const newErrors: Record<string, string> = {}

    // Validate name
    if (!name.trim()) {
      newErrors.name = "Nome é obrigatório"
    } else if (name.length < 3) {
      newErrors.name = "Nome deve ter pelo menos 3 caracteres"
    } else if (name.length > 60) {
      newErrors.name = "Nome deve ter no máximo 60 caracteres"
    }

    // Validate description (optional)
    if (description.length > 255) {
      newErrors.description = "Descrição deve ter no máximo 255 caracteres"
    }

    // Validate parameters
    const keyRegex = /^[a-zA-Z_][a-zA-Z0-9_]*$/
    const uniqueKeys = new Set<string>()

    parameters.forEach((param, index) => {
      if (!param.key.trim()) {
        newErrors[`param_${index}_key`] = "Chave é obrigatória"
      } else if (!keyRegex.test(param.key)) {
        newErrors[`param_${index}_key`] = "Chave deve começar com letra ou _ e conter apenas letras, números e _"
      } else if (uniqueKeys.has(param.key)) {
        newErrors[`param_${index}_key`] = "Chave deve ser única"
      } else {
        uniqueKeys.add(param.key)
      }
    })

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
  
    if (!validateForm()) return
  
    // Monta o corpo da requisição para a API
    const payload = {
      name,
      description,
      parameters: parameters.map((param) => ({
        name: param.key,
        type: param.type,
      })),
    }
  
    try {
      const response = await fetch("http://localhost:8000/pipelines", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      })
  
      if (!response.ok) {
        throw new Error(`Erro ao criar pipeline: ${response.statusText}`)
      }
  
      toast({
        title: "Pipeline criado com sucesso!",
        description: `O pipeline "${name}" foi registrado na API.`,
      })
  
      resetForm()
      router.push("/my-pipelines")
    } catch (error: any) {
      toast({
        title: "Erro",
        description: error.message ?? "Não foi possível criar o pipeline.",
        variant: "destructive",
      })
    }
  }  

  return (
    <div className="container mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Novo Pipeline</h1>
        <Button onClick={resetForm}>Novo</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Detalhes do Pipeline</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="name">
                Nome <span className="text-red-500">*</span>
              </Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Nome do pipeline"
                className={errors.name ? "border-red-500" : ""}
                aria-invalid={!!errors.name}
                aria-describedby={errors.name ? "name-error" : undefined}
              />
              {errors.name && (
                <p id="name-error" className="text-sm text-red-500">
                  {errors.name}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Descrição</Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Descrição do pipeline"
                className={errors.description ? "border-red-500" : ""}
                aria-invalid={!!errors.description}
                aria-describedby={errors.description ? "description-error" : undefined}
              />
              {errors.description && (
                <p id="description-error" className="text-sm text-red-500">
                  {errors.description}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label>Parâmetros</Label>
              <ParametersTable parameters={parameters} setParameters={setParameters} errors={errors} />
            </div>

            <div className="flex justify-end">
              <Button type="submit">Salvar Pipeline</Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
