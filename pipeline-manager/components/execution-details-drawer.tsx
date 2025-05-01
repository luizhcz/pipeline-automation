"use client"

import type { Execution } from "@/types/execution"
import { Button } from "@/components/ui/button"
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer"
import { ScrollArea } from "@/components/ui/scroll-area"
import StatusBadge from "@/components/status-badge"
import { formatDate } from "@/lib/utils"

interface ExecutionDetailsDrawerProps {
  execution: Execution | null
  open: boolean
  onClose: () => void
}

export default function ExecutionDetailsDrawer({ execution, open, onClose }: ExecutionDetailsDrawerProps) {
  if (!execution) return null

  return (
    <Drawer open={open} onOpenChange={onClose}>
      <DrawerContent className="max-h-[90vh]">
        <DrawerHeader>
          <DrawerTitle className="flex items-center justify-between">
            <span>Detalhes da Execução</span>
            <StatusBadge status={execution.status} />
          </DrawerTitle>
          <DrawerDescription>
            {execution.pipelineName} ({execution.version}) - {execution.requestId}
          </DrawerDescription>
        </DrawerHeader>
        <div className="px-4 py-2">
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Criado em</p>
              <p>{formatDate(execution.createdAt, true)}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Iniciado em</p>
              <p>{execution.startedAt ? formatDate(execution.startedAt, true) : "N/A"}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Finalizado em</p>
              <p>{execution.finishedAt ? formatDate(execution.finishedAt, true) : "N/A"}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Tipo de saída</p>
              <p>{execution.outputType || "N/A"}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Tentativas</p>
              <p>{execution.retryCount}</p>
            </div>
          </div>

          <div className="mb-4">
            <p className="text-sm font-medium text-muted-foreground mb-2">Parâmetros</p>
            <div className="bg-muted rounded-md p-3">
              <pre className="text-xs whitespace-pre-wrap">{JSON.stringify(execution.params, null, 2)}</pre>
            </div>
          </div>

          {execution.status === "FAILURE" && execution.error && (
            <div className="mb-4">
              <p className="text-sm font-medium text-red-500 mb-2">Erro</p>
              <div className="bg-red-50 text-red-800 rounded-md p-3">
                <p className="text-sm">{execution.error}</p>
              </div>
            </div>
          )}

          <div>
            <p className="text-sm font-medium text-muted-foreground mb-2">Logs</p>
            <ScrollArea className="h-[200px] rounded-md border">
              <div className="p-3 font-mono">
              {execution.logs.map((log, idx) => (
                <div key={idx} className="flex space-x-2 text-sm">
                  <span
                    className={
                      log.mensagem.includes("[ERROR]")
                        ? "text-red-600"
                        : log.mensagem.includes("[WARNING]")
                        ? "text-yellow-600"
                        : ""
                    }
                  >
                    {log.mensagem}
                  </span>
                  <span className="text-muted-foreground">
                    — {formatDate(new Date(log.data))}
                  </span>
                </div>
              ))}
              </div>
            </ScrollArea>
          </div>
        </div>
        <DrawerFooter>
          <DrawerClose asChild>
            <Button variant="outline">Fechar</Button>
          </DrawerClose>
        </DrawerFooter>
      </DrawerContent>
    </Drawer>
  )
}
