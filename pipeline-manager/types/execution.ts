export type ExecutionStatus = "PENDING" | "STARTED" | "SUCCESS" | "FAILURE"

export interface Execution {
  requestId: string
  pipelineName: string
  version: string
  params: string     // json string – exibimos só se necessário
  status: ExecutionStatus
  retryCount: number
  createdAt: Date
  startedAt?: Date | null
  finishedAt?: Date | null
  outputType?: string | null
  outputPath?: string | null
  error?: string | null
  logs: LogEntry[]
}

/** Filtros vindos da UI – continuam iguais */
export interface ExecutionFilter {
  search?: string
  status?: ExecutionStatus | "ALL"
  dateFrom?: Date
  dateTo?: Date
}

export interface LogEntry {
  mensagem: string
  data: string       // ISO
}