"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import type { Pipeline, ParameterType, ExecutionResult } from "@/types/pipeline"

interface ExecutionFormProps {
  pipeline: Pipeline
  onExecute: (parameters: Record<string, any>) => Promise<ExecutionResult>
}

export default function ExecutionForm({ pipeline, onExecute }: ExecutionFormProps) {
  const [values, setValues] = useState<Record<string, any>>({})
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [isExecuting, setIsExecuting] = useState(false)
  const [result, setResult] = useState<ExecutionResult | null>(null)

  const getInputTypeForParameterType = (type: ParameterType): string => {
    switch (type) {
      case "int":
      case "number":
      case "float":
        return "number"
      default:
        return "text"
    }
  }

  const getPlaceholderForType = (type: ParameterType): string => {
    switch (type) {
      case "int":
        return "42"
      case "number":
      case "float":
        return "3.14"
      case "string":
        return "texto"
      case "list":
        return "[1, 2, 3]"
      case "dict":
        return '{"chave": "valor"}'
      default:
        return ""
    }
  }

  const handleValueChange = (key: string, value: string, type: ParameterType) => {
    setValues((prev) => ({ ...prev, [key]: value }))

    // Clear error when user starts typing
    if (errors[key]) {
      setErrors((prev) => {
        const newErrors = { ...prev }
        delete newErrors[key]
        return newErrors
      })
    }
  }

  const validateValues = (): boolean => {
    const newErrors: Record<string, string> = {}

    pipeline.parameters.forEach((param) => {
      const value = values[param.key]

      if (value === undefined || value === "") {
        newErrors[param.key] = "Valor é obrigatório"
        return
      }

      try {
        validateParameterValue(param.key, value, param.type)
      } catch (error) {
        if (error instanceof Error) {
          newErrors[param.key] = error.message
        }
      }
    })

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const validateParameterValue = (key: string, value: string, type: ParameterType) => {
    switch (type) {
      case "int":
        if (!Number.isInteger(Number(value))) {
          throw new Error("Valor deve ser um número inteiro")
        }
        break
      case "number":
      case "float":
        if (isNaN(Number(value))) {
          throw new Error("Valor deve ser um número")
        }
        break
      case "list":
        try {
          const parsed = JSON.parse(value)
          if (!Array.isArray(parsed)) {
            throw new Error("Valor deve ser um array JSON válido")
          }
        } catch {
          throw new Error("Valor deve ser um array JSON válido")
        }
        break
      case "dict":
        try {
          const parsed = JSON.parse(value)
          if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
            throw new Error("Valor deve ser um objeto JSON válido")
          }
        } catch {
          throw new Error("Valor deve ser um objeto JSON válido")
        }
        break
    }
  }

  const processValues = (): Record<string, any> => {
    const processedValues: Record<string, any> = {}

    pipeline.parameters.forEach((param) => {
      const value = values[param.key]

      if (value !== undefined) {
        switch (param.type) {
          case "int":
            processedValues[param.key] = Number.parseInt(value)
            break
          case "number":
          case "float":
            processedValues[param.key] = Number.parseFloat(value)
            break
          case "list":
          case "dict":
            processedValues[param.key] = JSON.parse(value)
            break
          default:
            processedValues[param.key] = value
        }
      }
    })

    return processedValues
  }

  const handleExecute = async () => {
    if (!validateValues()) return

    setIsExecuting(true)
    setResult(null)

    try {
      const processedValues = processValues()
      const executionResult = await onExecute(processedValues)
      setResult(executionResult)
    } catch (error) {
      setResult({
        success: false,
        message: "Erro ao executar pipeline",
        logs: [error instanceof Error ? error.message : "Erro desconhecido"],
      })
    } finally {
      setIsExecuting(false)
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Parâmetros de Execução</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {pipeline.parameters.map((param) => (
              <div key={param.key} className="space-y-2">
                <Label htmlFor={`param-${param.key}`}>
                  {param.key} <span className="text-muted-foreground">({param.type})</span>
                </Label>
                {param.type === "list" || param.type === "dict" ? (
                  <Textarea
                    id={`param-${param.key}`}
                    value={values[param.key] || ""}
                    onChange={(e) => handleValueChange(param.key, e.target.value, param.type)}
                    placeholder={getPlaceholderForType(param.type)}
                    className={errors[param.key] ? "border-red-500" : ""}
                    aria-invalid={!!errors[param.key]}
                  />
                ) : (
                  <Input
                    id={`param-${param.key}`}
                    type={getInputTypeForParameterType(param.type)}
                    value={values[param.key] || ""}
                    onChange={(e) => handleValueChange(param.key, e.target.value, param.type)}
                    placeholder={getPlaceholderForType(param.type)}
                    className={errors[param.key] ? "border-red-500" : ""}
                    aria-invalid={!!errors[param.key]}
                  />
                )}
                {errors[param.key] && <p className="text-xs text-red-500 mt-1">{errors[param.key]}</p>}
              </div>
            ))}
          </div>
        </CardContent>
        <CardFooter>
          <Button onClick={handleExecute} disabled={isExecuting}>
            {isExecuting ? "Executando..." : "Executar Pipeline"}
          </Button>
        </CardFooter>
      </Card>

      {result && (
        <Card className={result.success ? "border-green-500" : "border-red-500"}>
          <CardHeader>
            <CardTitle className={result.success ? "text-green-500" : "text-red-500"}>
              {result.success ? "Execução bem-sucedida" : "Erro na execução"}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="mb-2">{result.message}</p>
            {result.logs && result.logs.length > 0 && (
              <div className="bg-muted p-3 rounded-md overflow-auto max-h-40">
                <pre className="text-xs">
                  {result.logs.map((log, index) => (
                    <div key={index}>{log}</div>
                  ))}
                </pre>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
