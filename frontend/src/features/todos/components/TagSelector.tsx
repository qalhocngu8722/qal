import { X, Plus, Check } from "lucide-react";
import { useTags, useAttachTag, useDetachTag } from "@/features/tags/api/tags";
import type { Tag } from "@/features/tags/api/tags";

interface TagSelectorProps {
  todoId: string;
  currentTags: Tag[];
  onClose: () => void;
}

export function TagSelector({ todoId, currentTags, onClose }: TagSelectorProps) {
  const { data: tagsData } = useTags();
  const attachTag = useAttachTag();
  const detachTag = useDetachTag();

  const currentTagIds = new Set(currentTags.map((t) => t.id));

  const handleToggleTag = (tagId: string) => {
    if (currentTagIds.has(tagId)) {
      detachTag.mutate({ todoId, tagId });
    } else {
      attachTag.mutate({ todoId, tagId });
    }
  };

  return (
    <div className="absolute right-0 top-full mt-2 z-50 w-64 bg-white dark:bg-gray-800 border rounded-lg shadow-lg p-3">
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-semibold text-sm">Manage Tags</h4>
        <button
          onClick={onClose}
          className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
        >
          <X size={14} />
        </button>
      </div>

      <div className="space-y-1 max-h-64 overflow-y-auto">
        {tagsData?.items.map((tag) => {
          const isAttached = currentTagIds.has(tag.id);
          return (
            <button
              key={tag.id}
              onClick={() => handleToggleTag(tag.id)}
              className="w-full flex items-center justify-between p-2 hover:bg-gray-50 dark:hover:bg-gray-700 rounded text-sm"
            >
              <div className="flex items-center gap-2">
                {tag.color && (
                  <div
                    className="w-3 h-3 rounded"
                    style={{ backgroundColor: tag.color }}
                  />
                )}
                <span>{tag.name}</span>
              </div>
              {isAttached ? (
                <Check size={16} className="text-green-600" />
              ) : (
                <Plus size={16} className="text-gray-400" />
              )}
            </button>
          );
        })}
        {tagsData?.items.length === 0 && (
          <p className="text-sm text-gray-500 text-center py-2">
            No tags available. Create one first!
          </p>
        )}
      </div>
    </div>
  );
}
