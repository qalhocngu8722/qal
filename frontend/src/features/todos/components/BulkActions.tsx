import { CheckCheck, X } from "lucide-react";
import { useBulkUpdateStatus } from "../api/todos";

interface BulkActionsProps {
  selectedIds: string[];
  onClearSelection: () => void;
}

export function BulkActions({ selectedIds, onClearSelection }: BulkActionsProps) {
  const bulkUpdate = useBulkUpdateStatus();

  const handleBulkComplete = () => {
    bulkUpdate.mutate(
      { todo_ids: selectedIds, completed: true },
      {
        onSuccess: () => {
          onClearSelection();
        },
      }
    );
  };

  const handleBulkActivate = () => {
    bulkUpdate.mutate(
      { todo_ids: selectedIds, completed: false },
      {
        onSuccess: () => {
          onClearSelection();
        },
      }
    );
  };

  if (selectedIds.length === 0) return null;

  return (
    <div className="fixed bottom-4 left-1/2 transform -translate-x-1/2 bg-white border shadow-lg rounded-lg px-6 py-3 flex items-center gap-4">
      <span className="text-sm font-medium">
        {selectedIds.length} selected
      </span>
      <div className="flex items-center gap-2">
        <button
          onClick={handleBulkComplete}
          disabled={bulkUpdate.isPending}
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 text-sm"
        >
          <CheckCheck size={16} />
          Mark Complete
        </button>
        <button
          onClick={handleBulkActivate}
          disabled={bulkUpdate.isPending}
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 disabled:opacity-50 text-sm"
        >
          <X size={16} />
          Mark Active
        </button>
        <button
          onClick={onClearSelection}
          className="px-4 py-2 border rounded hover:bg-gray-50 text-sm"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
