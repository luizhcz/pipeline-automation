"use client"

import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Card, CardContent } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Calendar } from "@/components/ui/calendar"
import { format } from "date-fns"
import { ptBR } from "date-fns/locale"
import { CalendarIcon, Download, Info, Search } from "lucide-react"
import { cn, formatDate } from "@/lib/utils"
import { useToast } from "@/components/ui/use-toast"
import StatusBadge from "@/components/status-badge"
import CountdownTimer from "@/components/countdown-timer"
import ExecutionDetailsDrawer from "@/components/execution-details-drawer"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import type { Execution, ExecutionFilter } from "@/types/execution"
import { fetchExecutions, downloadFile } from "@/lib/execution-client"

export default function MonitorExecutions() {
  /* ---------------------------- STATE ---------------------------- */
  const [executions, setExecutions] = useState<Execution[]>([])
  const [totalExecutions, setTotalExecutions] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize] = useState(10)

  const [filters, setFilters] = useState<ExecutionFilter>({
    search: "",
    status: "ALL",
    dateFrom: undefined,
    dateTo: undefined,
  })

  const [autoRefresh, setAutoRefresh] = useState(true)

  const [selectedExecution, setSelectedExecution] = useState<Execution | null>(null)
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)

  const { toast } = useToast()

  /* ---------------------------- HELPERS --------------------------- */
  const isDownloadAvailable = (execution: Execution): boolean => {
    if (execution.status !== "SUCCESS" || !execution.finishedAt) return false
    const threeHours = 3 * 60 * 60 * 1000
    return Date.now() - execution.finishedAt.getTime() <= threeHours
  }

  const getExpiryDate = (finishedAt: Date): Date => {
    return new Date(finishedAt.getTime() + 3 * 60 * 60 * 1000)
  }

  /* ------------------------- DATA LOADERS ------------------------ */
  const loadExecutions = async () => {
    try {
      const { executions: list, total } = await fetchExecutions(filters, currentPage, pageSize)
      setExecutions(list)
      setTotalExecutions(total)
    } catch (err) {
      toast({
        variant: "destructive",
        title: "Erro ao buscar execuções",
        description: String(err),
      })
    }
  }

  /* --------------------------- EFFECTS --------------------------- */
  useEffect(() => {
    loadExecutions()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters, currentPage, pageSize])

  useEffect(() => {
    if (!autoRefresh) return
    const id = setInterval(loadExecutions, 10_000)
    return () => clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRefresh, filters, currentPage, pageSize])

  /* ------------------------- EVENT HANDLERS ---------------------- */
  const handleFilterChange = (key: keyof ExecutionFilter, value: any) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
    setCurrentPage(1)
  }

  const handleDownload = async (execution: Execution) => {
    if (!isDownloadAvailable(execution)) return
    try {
      const blob = await downloadFile(execution.requestId)
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = execution.outputPath ?? `output.${execution.outputType ?? "bin"}`
      a.click()
      URL.revokeObjectURL(url)
      toast({
        title: "Download iniciado",
        description: `Baixando arquivo da execução ${execution.requestId}`,
      })
    } catch (err) {
      toast({
        variant: "destructive",
        title: "Erro ao baixar arquivo",
        description: String(err),
      })
    }
  }

  const handleShowDetails = (execution: Execution) => {
    setSelectedExecution(execution)
    setIsDrawerOpen(true)
  }

  /* ----------------------------- JSX ----------------------------- */
  const totalPages = Math.ceil(totalExecutions / pageSize)

  return (
    <div className="container mx-auto">
      <h1 className="text-3xl font-bold mb-6">Monitorar Execuções</h1>

      {/* Toolbar */}
      <Card className="mb-6">
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar por ID, pipeline ou versão"
                className="pl-8"
                value={filters.search || ""}
                onChange={(e) => handleFilterChange("search", e.target.value)}
              />
            </div>

            {/* Status filter */}
            <Select value={filters.status || "ALL"} onValueChange={(v) => handleFilterChange("status", v)}>
              <SelectTrigger>
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">Todos os status</SelectItem>
                <SelectItem value="PENDING">Pendente</SelectItem>
                <SelectItem value="STARTED">Em execução</SelectItem>
                <SelectItem value="SUCCESS">Sucesso</SelectItem>
                <SelectItem value="FAILURE">Falha</SelectItem>
              </SelectContent>
            </Select>

            {/* Date from */}
            <Popover>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  className={cn("justify-start text-left font-normal", !filters.dateFrom && "text-muted-foreground")}
                >
                  <CalendarIcon className="mr-2 h-4 w-4" />
                  {filters.dateFrom ? format(filters.dateFrom, "PPP", { locale: ptBR }) : "Data inicial"}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0">
                <Calendar
                  mode="single"
                  selected={filters.dateFrom || undefined}
                  onSelect={(date) => handleFilterChange("dateFrom", date)}
                  initialFocus
                />
              </PopoverContent>
            </Popover>

            {/* Date to */}
            <Popover>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  className={cn("justify-start text-left font-normal", !filters.dateTo && "text-muted-foreground")}
                >
                  <CalendarIcon className="mr-2 h-4 w-4" />
                  {filters.dateTo ? format(filters.dateTo, "PPP", { locale: ptBR }) : "Data final"}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0">
                <Calendar
                  mode="single"
                  selected={filters.dateTo || undefined}
                  onSelect={(date) => handleFilterChange("dateTo", date)}
                  initialFocus
                />
              </PopoverContent>
            </Popover>
          </div>

          <div className="flex justify-between items-center mt-4">
            <div className="flex items-center space-x-2">
              <Switch id="auto-refresh" checked={autoRefresh} onCheckedChange={setAutoRefresh} />
              <Label htmlFor="auto-refresh">Atualização automática (10s)</Label>
            </div>
            <Button
              variant="outline"
              onClick={() => {
                loadExecutions()
                toast({
                  title: "Dados atualizados",
                  description: "As informações de execução foram atualizadas.",
                })
              }}
            >
              Atualizar agora
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Executions Table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Pipeline</TableHead>
              <TableHead>Versão</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Criado em</TableHead>
              <TableHead>Finalizado em</TableHead>
              <TableHead>Tipo</TableHead>
              <TableHead>Disponibilidade</TableHead>
              <TableHead className="text-right">Ações</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {executions.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                  Nenhuma execução encontrada com os filtros selecionados.
                </TableCell>
              </TableRow>
            ) : (
              executions.map((execution) => {
                const isExpired = execution.finishedAt && !isDownloadAvailable(execution)
                return (
                  <TableRow
                    key={execution.requestId}
                    className={cn(
                      isExpired && "text-muted-foreground bg-muted/30",
                      "hover:bg-muted/50 cursor-pointer",
                    )}
                    onClick={() => handleShowDetails(execution)}
                  >
                    <TableCell className="font-medium">{execution.pipelineName}</TableCell>
                    <TableCell>{execution.version}</TableCell>
                    <TableCell>
                      <StatusBadge status={execution.status} />
                    </TableCell>
                    <TableCell>{formatDate(execution.createdAt)}</TableCell>
                    <TableCell>{execution.finishedAt ? formatDate(execution.finishedAt) : "-"}</TableCell>
                    <TableCell>{execution.outputType || "-"}</TableCell>
                    <TableCell>
                      {execution.status === "SUCCESS" && execution.finishedAt ? (
                        isDownloadAvailable(execution) ? (
                          <CountdownTimer expiryDate={getExpiryDate(execution.finishedAt)} />
                        ) : (
                          "Expirado"
                        )
                      ) : (
                        "-"
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end space-x-2" onClick={(e) => e.stopPropagation()}>
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button variant="ghost" size="icon" onClick={() => handleShowDetails(execution)}>
                                <Info className="h-4 w-4" />
                                <span className="sr-only">Detalhes</span>
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>Ver detalhes</TooltipContent>
                          </Tooltip>
                        </TooltipProvider>

                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                variant="ghost"
                                size="icon"
                                disabled={!isDownloadAvailable(execution)}
                                onClick={() => handleDownload(execution)}
                              >
                                <Download className="h-4 w-4" />
                                <span className="sr-only">Download</span>
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>
                              {isDownloadAvailable(execution)
                                ? "Baixar arquivo"
                                : execution.status === "SUCCESS"
                                ? "Arquivo expirado"
                                : "Download indisponível"}
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      </div>
                    </TableCell>
                  </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-between items-center mt-4">
          <div className="text-sm text-muted-foreground">
            Mostrando {(currentPage - 1) * pageSize + 1} a {Math.min(currentPage * pageSize, totalExecutions)} de {totalExecutions}
            {" "}execuções
          </div>
          <div className="flex space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
              disabled={currentPage === 1}
            >
              Anterior
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage((prev) => Math.min(prev + 1, totalPages))}
              disabled={currentPage === totalPages}
            >
              Próxima
            </Button>
          </div>
        </div>
      )}

      {/* Execution Details Drawer */}
      <ExecutionDetailsDrawer
        execution={selectedExecution}
        open={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
      />
    </div>
  )
}