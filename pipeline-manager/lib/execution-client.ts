import { Execution, ExecutionFilter } from "@/types/execution"

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

function mapTaskToExecution(raw: any): Execution {
  return {
    requestId:        raw.request_id,
    pipelineName:     raw.notebook_name,
    version:          raw.version,
    params:           raw.params,
    status:           raw.status,
    retryCount:       raw.retry_count,
    createdAt:        new Date(raw.created_at),
    startedAt:        raw.started_at   ? new Date(raw.started_at)   : null,
    finishedAt:       raw.finished_at  ? new Date(raw.finished_at)  : null,
    outputType:       raw.output_type,
    outputPath:       raw.output_path,
    error:            raw.error,
    logs:             raw.logs ?? [],
  }
}

/**
 * Busca execuções aplicando paginação e filtros do lado do cliente.
 * Caso queira filtros server-side, ajuste a API e passe query-params aqui.
 */
export async function fetchExecutions(
  filters: ExecutionFilter,
  page: number,
  pageSize: number,
): Promise<{ executions: Execution[]; total: number }> {
  // 1. traz tudo (simples) – se o dataset ficar grande, adicione paginação server-side
  const res = await fetch(`${API_BASE}/tasks`, { next: { revalidate: 0 } })
  if (!res.ok) throw new Error("Falha ao buscar execuções")

  const data: any[] = await res.json()

  // 2. converte
  let executions = data.map(mapTaskToExecution) as Execution[]

  // 3. aplica filtros (client-side)
  if (filters.search) {
    const s = filters.search.toLowerCase()
    executions = executions.filter(
      (e) =>
        e.requestId.toLowerCase().includes(s) ||
        e.pipelineName.toLowerCase().includes(s) ||
        e.version.toLowerCase().includes(s),
    )
  }

  if (filters.status && filters.status !== "ALL") {
    executions = executions.filter((e) => e.status === filters.status)
  }

  if (filters.dateFrom) {
    executions = executions.filter((e) => e.createdAt >= filters.dateFrom!)
  }

  if (filters.dateTo) {
    const end = new Date(filters.dateTo)
    end.setHours(23, 59, 59, 999)
    executions = executions.filter((e) => e.createdAt <= end)
  }

  // 4. ordena por createdAt DESC (opcional)
  executions.sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime())

  // 5. pagina
  const total = executions.length
  const offset = (page - 1) * pageSize
  executions = executions.slice(offset, offset + pageSize)

  return { executions, total }
}

/** Download genérico – ajusta rota se existir algo como /tasks/{id}/download */
export async function downloadFile(requestId: string): Promise<Blob> {
  const res = await fetch(`${API_BASE}/tasks/${requestId}/download`)
  if (!res.ok) throw new Error("Falha no download")
  return res.blob()
}