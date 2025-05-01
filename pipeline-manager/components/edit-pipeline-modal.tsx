"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { useToast } from "@/components/ui/use-toast"
import { usePipelineStore } from "@/context/pipeline-store"
import ParametersTable from "@/components/parameters-table"
import type { Pipeline, PipelineParameter } from "@/types/pipeline"

interface EditPipelineModalProps {
  pipeline: Pipeline
  isOpen: boolean
  onClose: () => void
}

export default function EditPipelineModal({ pipeline, isOpen, onClose }: EditPipelineModalProps) {
  const { updatePipeline, deletePipeline } = usePipelineStore()
  const { toast } = useToast()

  const [name, setName] = useState(pipeline.name)
  const [description, setDescription] = useState(pipeline.description)
  const [parameters, setParameters] = useState<PipelineParameter[]>(
    pipeline.parameters.map((param) => ({
      ...param,
      value: null,
    })),
  )
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)

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

  const handleSave = () => {
    if (validateForm()) {
      // Set all parameter values to null
      const processedParams = parameters.map((param) => ({
        ...param,
        value: null,
      }))

      const updatedPipeline: Pipeline = {
        ...pipeline,
        name,
        description,
        parameters: processedParams,
      }

      updatePipeline(updatedPipeline)

      toast({
        title: "Pipeline atualizado",
        description: `O pipeline "${name}" foi atualizado com sucesso.`,
      })

      onClose()
    }
  }

  const handleDelete = () => {
    deletePipeline(pipeline.id)

    toast({
      title: "Pipeline excluído",
      description: `O pipeline "${pipeline.name}" foi excluído com sucesso.`,
    })

    setIsDeleteDialogOpen(false)
    onClose()
  }

  return (
    <>
      <Dialog open={isOpen} onOpenChange={onClose}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Editar Pipeline</DialogTitle>
            <DialogDescription>Edite os detalhes e parâmetros do seu pipeline.</DialogDescription>
          </DialogHeader>

          <div className="space-y-6 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-name">
                Nome <span className="text-red-500">*</span>
              </Label>
              <Input
                id="edit-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className={errors.name ? "border-red-500" : ""}
                aria-invalid={!!errors.name}
              />
              {errors.name && <p className="text-sm text-red-500">{errors.name}</p>}
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit-description">Descrição</Label>
              <Textarea
                id="edit-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className={errors.description ? "border-red-500" : ""}
                aria-invalid={!!errors.description}
              />
              {errors.description && <p className="text-sm text-red-500">{errors.description}</p>}
            </div>

            <div className="space-y-2">
              <Label>Parâmetros</Label>
              <ParametersTable parameters={parameters} setParameters={setParameters} errors={errors} />
            </div>
          </div>

          <DialogFooter className="flex justify-between sm:justify-between">
            <Button variant="destructive" onClick={() => setIsDeleteDialogOpen(true)}>
              Excluir Pipeline
            </Button>
            <div className="flex gap-2">
              <Button variant="outline" onClick={onClose}>
                Cancelar
              </Button>
              <Button onClick={handleSave}>Salvar Alterações</Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirmar exclusão</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja excluir o pipeline "{pipeline.name}"? Esta ação não pode ser desfeita.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Excluir
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
