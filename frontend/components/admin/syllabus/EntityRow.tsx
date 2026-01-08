"use client";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Edit, Power, PowerOff, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface EntityRowProps {
  id: number;
  title: string;
  subtitle?: string;
  isActive: boolean;
  isSelected?: boolean;
  onSelect?: () => void;
  onEdit?: () => void;
  onToggle?: () => void;
  onDelete?: () => void;
  showDelete?: boolean;
  className?: string;
}

export function EntityRow({
  id,
  title,
  subtitle,
  isActive,
  isSelected = false,
  onSelect,
  onEdit,
  onToggle,
  onDelete,
  showDelete = false,
  className,
}: EntityRowProps) {
  return (
    <div
      className={cn(
        "flex items-center justify-between p-3 rounded-lg border transition-colors",
        isSelected && "bg-primary/10 border-primary",
        !isSelected && "hover:bg-muted/50",
        !isActive && "opacity-60",
        className
      )}
      onClick={onSelect}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="font-medium text-sm truncate">{title}</p>
          <Badge variant={isActive ? "default" : "secondary"} className="text-xs">
            {isActive ? "Active" : "Inactive"}
          </Badge>
        </div>
        {subtitle && (
          <p className="text-xs text-muted-foreground mt-1 truncate">{subtitle}</p>
        )}
      </div>
      <div className="flex items-center gap-1 ml-2" onClick={(e) => e.stopPropagation()}>
        {onEdit && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onEdit}
            className="h-8 w-8 p-0"
          >
            <Edit className="h-4 w-4" />
          </Button>
        )}
        {onToggle && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onToggle}
            className="h-8 w-8 p-0"
            title={isActive ? "Disable" : "Enable"}
          >
            {isActive ? (
              <PowerOff className="h-4 w-4 text-muted-foreground" />
            ) : (
              <Power className="h-4 w-4 text-muted-foreground" />
            )}
          </Button>
        )}
        {showDelete && onDelete && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onDelete}
            className="h-8 w-8 p-0 text-destructive hover:text-destructive"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
}
