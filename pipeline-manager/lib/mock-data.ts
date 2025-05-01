import type { Execution, ExecutionStatus } from "@/types/execution"
import { v4 as uuidv4 } from "uuid"

// Helper to generate random dates within a range
const randomDate = (start: Date, end: Date): Date => {
  return new Date(start.getTime() + Math.random() * (end.getTime() - start.getTime()))
}

// Helper to generate random status with weighted distribution
const randomStatus = (): ExecutionStatus => {
  const rand = Math.random()
  if (rand < 0.1) return "PENDING"
  if (rand < 0.2) return "RUNNING"
  if (rand < 0.7) return "SUCCESS"
  return "FAILURE"
}

// Generate a random parameter object
const generateRandomParams = (): Record<string, any> => {
  const paramTypes = ["int", "float", "string", "list", "dict"]
  const numParams = Math.floor(Math.random() * 5) + 1
  const params: Record<string, any> = {}

  for (let i = 0; i < numParams; i++) {
    const paramType = paramTypes[Math.floor(Math.random() * paramTypes.length)]
    const paramKey = `param_${i + 1}`

    switch (paramType) {
      case "int":
        params[paramKey] = Math.floor(Math.random() * 100)
        break
      case "float":
        params[paramKey] = Math.random() * 100
        break
      case "string":
        params[paramKey] = `value_${Math.floor(Math.random() * 1000)}`
        break
      case "list":
        params[paramKey] = Array.from({ length: Math.floor(Math.random() * 5) + 1 }, (_, i) => i)
        break
      case "dict":
        params[paramKey] = { key1: "value1", key2: Math.floor(Math.random() * 100) }
        break
    }
  }

  return params
}

// Generate random logs based on status
const generateLogs = (status: ExecutionStatus): string[] => {
  const logs: string[] = [
    "[INFO] Iniciando execução do pipeline",
    "[INFO] Carregando parâmetros",
    "[INFO] Validando parâmetros",
    "[INFO] Preparando ambiente de execução",
  ]

  if (status === "RUNNING") {
    logs.push("[INFO] Processando dados...")
  } else if (status === "SUCCESS") {
    logs.push(
      "[INFO] Processando dados...",
      "[INFO] Processamento concluído",
      "[INFO] Gerando arquivo de saída",
      `[INFO] Execução concluída com sucesso em ${(Math.random() * 10 + 1).toFixed(2)}s`,
    )
  } else if (status === "FAILURE") {
    logs.push(
      "[INFO] Processando dados...",
      "[ERROR] Falha ao processar dados",
      "[ERROR] Erro de execução: Parâmetros inválidos ou recursos insuficientes",
      "[ERROR] Execução interrompida",
    )
  }

  return logs
}

// Generate a list of mock executions
export const generateMockExecutions = (count: number): Execution[] => {
  const now = new Date()
  const pipelineNames = [
    "Treinamento ML",
    "ETL Dados",
    "Análise Preditiva",
    "Processamento de Imagens",
    "Extração de Texto",
  ]
  const outputTypes = ["CSV", "JSON", "Parquet", "Model", "Image", "Text", null]

  return Array.from({ length: count }, (_, i) => {
    const status = randomStatus()
    const createdAt = randomDate(new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000), now)

    let startedAt: Date | null = null
    let finishedAt: Date | null = null

    if (status !== "PENDING") {
      startedAt = new Date(createdAt.getTime() + Math.random() * 60 * 1000) // 0-60 minutes after creation

      if (status === "SUCCESS" || status === "FAILURE") {
        finishedAt = new Date(startedAt.getTime() + Math.random() * 120 * 60 * 1000) // 0-120 minutes after start
      }
    }

    return {
      requestId: uuidv4(),
      pipelineName: pipelineNames[Math.floor(Math.random() * pipelineNames.length)],
      version: `v${Math.floor(Math.random() * 5) + 1}.${Math.floor(Math.random() * 10)}`,
      params: generateRandomParams(),
      status,
      retryCount: Math.floor(Math.random() * 3),
      createdAt,
      startedAt,
      finishedAt,
      outputType: status === "SUCCESS" ? outputTypes[Math.floor(Math.random() * (outputTypes.length - 1))] : null,
      logs: generateLogs(status),
      errorMessage:
        status === "FAILURE" ? "Erro ao processar os dados: parâmetros inválidos ou recursos insuficientes" : undefined,
    }
  })
}

// Initial mock data
let mockExecutions = generateMockExecutions(50)

// Function to get executions with filtering and pagination
export const getMockExecutions = (
  filters: {
    search?: string
    status?: ExecutionStatus | "ALL"
    dateFrom?: Date
    dateTo?: Date
  } = {},
  page = 1,
  pageSize = 10,
): { executions: Execution[]; total: number } => {
  let filtered = [...mockExecutions]

  // Apply search filter
  if (filters.search) {
    const searchLower = filters.search.toLowerCase()
    filtered = filtered.filter(
      (exec) =>
        exec.requestId.toLowerCase().includes(searchLower) ||
        exec.pipelineName.toLowerCase().includes(searchLower) ||
        exec.version.toLowerCase().includes(searchLower),
    )
  }

  // Apply status filter
  if (filters.status && filters.status !== "ALL") {
    filtered = filtered.filter((exec) => exec.status === filters.status)
  }

  // Apply date range filter
  if (filters.dateFrom) {
    filtered = filtered.filter((exec) => exec.createdAt >= filters.dateFrom!)
  }
  if (filters.dateTo) {
    const dateTo = new Date(filters.dateTo)
    dateTo.setHours(23, 59, 59, 999)
    filtered = filtered.filter((exec) => exec.createdAt <= dateTo)
  }

  // Sort by finishedAt desc (most recent first)
  filtered.sort((a, b) => {
    if (!a.finishedAt && !b.finishedAt) return 0
    if (!a.finishedAt) return 1
    if (!b.finishedAt) return -1
    return b.finishedAt.getTime() - a.finishedAt.getTime()
  })

  // Calculate pagination
  const start = (page - 1) * pageSize
  const paginatedExecutions = filtered.slice(start, start + pageSize)

  return {
    executions: paginatedExecutions,
    total: filtered.length,
  }
}

// Function to get a single execution by ID
export const getMockExecutionById = (requestId: string): Execution | undefined => {
  return mockExecutions.find((exec) => exec.requestId === requestId)
}

// Function to simulate real-time updates by randomly changing some executions
export const updateMockExecutions = (): void => {
  mockExecutions = mockExecutions.map((exec) => {
    // Only update PENDING or RUNNING executions
    if (exec.status === "PENDING" || exec.status === "RUNNING") {
      const rand = Math.random()

      // 20% chance to update status
      if (rand < 0.2) {
        if (exec.status === "PENDING") {
          // PENDING -> RUNNING
          return {
            ...exec,
            status: "RUNNING",
            startedAt: new Date(),
            logs: [...exec.logs, "[INFO] Iniciando processamento de dados..."],
          }
        } else {
          // RUNNING -> SUCCESS or FAILURE
          const newStatus: ExecutionStatus = Math.random() < 0.8 ? "SUCCESS" : "FAILURE"
          const finishedAt = new Date()

          return {
            ...exec,
            status: newStatus,
            finishedAt,
            outputType:
              newStatus === "SUCCESS" ? ["CSV", "JSON", "Parquet", "Model"][Math.floor(Math.random() * 4)] : null,
            logs: generateLogs(newStatus),
            errorMessage:
              newStatus === "FAILURE"
                ? "Erro ao processar os dados: parâmetros inválidos ou recursos insuficientes"
                : undefined,
          }
        }
      }

      // For RUNNING executions, 50% chance to add a new log entry
      if (exec.status === "RUNNING" && rand < 0.5) {
        return {
          ...exec,
          logs: [...exec.logs, `[INFO] Progresso: ${Math.floor(Math.random() * 100)}%`],
        }
      }
    }

    return exec
  })

  // 10% chance to add a new execution
  if (Math.random() < 0.1) {
    const newExecution = generateMockExecutions(1)[0]
    mockExecutions = [newExecution, ...mockExecutions]
  }
}

// Function to simulate downloading a file
export const downloadMockFile = async (requestId: string): Promise<{ success: boolean; message?: string }> => {
  const execution = getMockExecutionById(requestId)

  if (!execution) {
    return { success: false, message: "Execução não encontrada" }
  }

  if (execution.status !== "SUCCESS") {
    return { success: false, message: "Arquivo disponível apenas para execuções bem-sucedidas" }
  }

  if (!execution.finishedAt) {
    return { success: false, message: "Execução não finalizada" }
  }

  const now = new Date()
  const threeHoursInMs = 3 * 60 * 60 * 1000

  if (now.getTime() - execution.finishedAt.getTime() > threeHoursInMs) {
    return { success: false, message: "Arquivo expirado (disponível por até 3 horas após a conclusão)" }
  }

  // Simulate successful download
  return { success: true }
}
