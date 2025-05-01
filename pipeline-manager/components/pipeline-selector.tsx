"use client"

import { useState } from "react"
import { Check, ChevronsUpDown } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { cn } from "@/lib/utils"
import type { Pipeline } from "@/types/pipeline"

interface PipelineSelectorProps {
  pipelines: Pipeline[]
  selectedPipelineId: string | null
  onSelect: (pipelineId: string) => void
}

export default function PipelineSelector({ pipelines, selectedPipelineId, onSelect }: PipelineSelectorProps) {
  const [open, setOpen] = useState(false)

  const selectedPipeline = pipelines.find((pipeline) => pipeline.id === selectedPipelineId)

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" role="combobox" aria-expanded={open} className="w-full justify-between">
          {selectedPipeline ? selectedPipeline.name : "Selecione um pipeline..."}
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-full p-0">
        <Command>
          <CommandInput placeholder="Buscar pipeline..." />
          <CommandList>
            <CommandEmpty>Nenhum pipeline encontrado.</CommandEmpty>
            <CommandGroup>
              {pipelines.map((pipeline) => (
                <CommandItem
                  key={pipeline.id}
                  value={pipeline.id}
                  onSelect={() => {
                    onSelect(pipeline.id)
                    setOpen(false)
                  }}
                >
                  <Check
                    className={cn("mr-2 h-4 w-4", selectedPipelineId === pipeline.id ? "opacity-100" : "opacity-0")}
                  />
                  {pipeline.name}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
