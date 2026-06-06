import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { Pencil, Trash2, Tag as TagIcon } from "lucide-react";
import type { Todo } from "../api/todos";
import { TagSelector } from "./TagSelector";
import { useState } from "react";

interface TodoItemProps {
  todo: Todo;
  index: number;
  onToggle: (todo: Todo) => void;
  onEdit: (todo: Todo) => void;
  onDelete: (id: string) => void;
  isSelected?: boolean;
  onSelect?: (id: string, selected: boolean) => void;
}

export function TodoItem({ 
  todo, 
  onToggle, 
  onEdit, 
  onDelete,
  isSelected = false,
  onSelect,
}: TodoItemProps) {
  const [showTagSelector, setShowTagSelector] = useState(false);

  return (
    <div className="relative flex items-center gap-3 p-3 rounded-lg border bg-card hover:bg-accent/50 transition-colors group">
      

      <Checkbox
        id={`todo-${todo.id}`}
        checked={todo.completed}
        onCheckedChange={() => onToggle(todo)}
      />

      <div className="flex-1 min-w-0">
        <label
          htmlFor={`todo-${todo.id}`}
          className={`text-sm font-medium cursor-pointer ${
            todo.completed ? "line-through text-muted-foreground" : ""
          }`}
        >
          {todo.title}
        </label>
        {todo.description && (
          <p className="text-xs text-muted-foreground mt-0.5 truncate">
            {todo.description}
          </p>
        )}
        {todo.tags && todo.tags.length > 0 && (
          <div className="flex items-center gap-1 mt-1 flex-wrap">
            {todo.tags.map((tag) => (
              <span
                key={tag.id}
                className="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full border"
                style={{
                  backgroundColor: tag.color ? `${tag.color}20` : undefined,
                  borderColor: tag.color || undefined,
                }}
              >
                {tag.name}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="relative flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={() => setShowTagSelector(!showTagSelector)}
        >
          <TagIcon className="h-3.5 w-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={() => onEdit(todo)}
        >
          <Pencil className="h-3.5 w-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-destructive hover:text-destructive"
          onClick={() => onDelete(todo.id)}
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>

        {showTagSelector && (
          <TagSelector
            todoId={todo.id}
            currentTags={todo.tags}
            onClose={() => setShowTagSelector(false)}
          />
        )}
      </div>
    </div>
  );
}
