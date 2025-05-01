"use client"

import type React from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { PipelineParameter, ParameterType } from "@/types/pipeline"
import { Plus, Trash2 } from "lucide-react"

interface ParametersTableProps {
  parameters: PipelineParameter[]
  setParameters: React.Dispatch<React.SetStateAction<PipelineParameter[]>>
  errors: Record<string, string>
}

export default function ParametersTable({ parameters, setParameters, errors }: ParametersTableProps) {
  const parameterTypes: { value: ParameterType; label: string }[] = [
    { value: "int", label: "Inteiro" },
    { value: "number", label: "Numérico" },
    { value: "float", label: "Flutuante" },
    { value: "string", label: "Texto" },
    { value: "list", label: "Lista" },
    { value: "dict", label: "Dicionário" },
  ]

  const addParameter = () => {
    setParameters([...parameters, { key: "", type: "string", value: null }])
  }

  const removeParameter = (index: number) => {
    setParameters(parameters.filter((_, i) => i !== index))
  }

  const updateParameter = (index: number, field: keyof PipelineParameter, value: string | ParameterType) => {
    const newParameters = [...parameters]
    newParameters[index] = {
      ...newParameters[index],
      [field]: value,
    }
    setParameters(newParameters)
  }

  return (
    <div className="space-y-4">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-1/2">Chave</TableHead>
            <TableHead className="w-1/2">Tipo</TableHead>
            <TableHead className="w-[50px]"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {parameters.length === 0 ? (
            <TableRow>
              <TableCell colSpan={3} className="text-center text-muted-foreground">
                Nenhum parâmetro adicionado
              </TableCell>
            </TableRow>
          ) : (
            parameters.map((param, index) => (
              <TableRow key={index}>
                <TableCell>
                  <Input
                    value={param.key}
                    onChange={(e) => updateParameter(index, "key", e.target.value)}
                    placeholder="nome_parametro"
                    className={errors[`param_${index}_key`] ? "border-red-500" : ""}
                    aria-invalid={!!errors[`param_${index}_key`]}
                  />
                  {errors[`param_${index}_key`] && (
                    <p className="text-xs text-red-500 mt-1">{errors[`param_${index}_key`]}</p>
                  )}
                </TableCell>
                <TableCell>
                  <Select
                    value={param.type}
                    onValueChange={(value) => updateParameter(index, "type", value as ParameterType)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Selecione o tipo" />
                    </SelectTrigger>
                    <SelectContent>
                      {parameterTypes.map((type) => (
                        <SelectItem key={type.value} value={type.value}>
                          {type.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </TableCell>
                <TableCell>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => removeParameter(index)}
                    aria-label="Remover parâmetro"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>

      <Button type="button" variant="outline" size="sm" className="flex items-center gap-1" onClick={addParameter}>
        <Plus className="h-4 w-4" />
        Adicionar Parâmetro
      </Button>
    </div>
  )
}
