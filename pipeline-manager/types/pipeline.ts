export type ParameterType = "int" | "number" | "float" | "string" | "list" | "dict"

export interface PipelineParameter {
  key: string
  type: ParameterType
  value?: any
}

export interface Pipeline {
  id: string
  name: string
  description: string
  created_at: Date
  parameters: PipelineParameter[]
}

export interface PipelineExecutionRequest {
  pipelineId: string
  parameters: Record<string, any>
}

export interface ExecutionResult {
  success: boolean
  message: string
  logs?: string[]
}
