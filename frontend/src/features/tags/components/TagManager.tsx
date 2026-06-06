import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Pencil, Trash2, Plus, X } from "lucide-react";
import { useTags, useCreateTag, useUpdateTag, useDeleteTag } from "../api/tags";
import { tagCreateSchema, type TagCreate } from "../schemas/tagSchema";
import type { Tag } from "../api/tags";

export function TagManager() {
  const { data: tagsData, isLoading } = useTags();
  const createTag = useCreateTag();
  const updateTag = useUpdateTag();
  const deleteTag = useDeleteTag();

  const [editingTag, setEditingTag] = useState<Tag | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);

  const createForm = useForm<TagCreate>({
    resolver: zodResolver(tagCreateSchema),
    defaultValues: { name: "", color: "" },
  });

  const editForm = useForm<TagCreate>({
    resolver: zodResolver(tagCreateSchema),
  });

  const handleCreate = (data: TagCreate) => {
    createTag.mutate(data, {
      onSuccess: () => {
        createForm.reset();
        setShowCreateForm(false);
      },
    });
  };

  const handleEdit = (tag: Tag) => {
    setEditingTag(tag);
    editForm.reset({ name: tag.name, color: tag.color || "" });
  };

  const handleUpdate = (data: TagCreate) => {
    if (!editingTag) return;
    updateTag.mutate(
      { id: editingTag.id, data },
      {
        onSuccess: () => {
          setEditingTag(null);
          editForm.reset();
        },
      }
    );
  };

  const handleDelete = (id: string) => {
    if (confirm("Are you sure you want to delete this tag?")) {
      deleteTag.mutate(id);
    }
  };

  if (isLoading) {
    return <div className="text-center py-4">Loading tags...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">Tags</h3>
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="inline-flex items-center gap-2 px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded hover:bg-primary/90"
        >
          {showCreateForm ? <X size={16} /> : <Plus size={16} />}
          {showCreateForm ? "Cancel" : "New Tag"}
        </button>
      </div>

      {showCreateForm && (
        <form
          onSubmit={createForm.handleSubmit(handleCreate)}
          className="border rounded-lg p-4 space-y-3"
        >
          <div>
            <label className="block text-sm font-medium mb-1">Name</label>
            <input
              {...createForm.register("name")}
              className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="Tag name"
            />
            {createForm.formState.errors.name && (
              <p className="text-sm text-red-500 mt-1">
                {createForm.formState.errors.name.message}
              </p>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Color (optional)</label>
            <input
              {...createForm.register("color")}
              type="color"
              className="w-20 h-10 border rounded cursor-pointer"
            />
          </div>
          <button
            type="submit"
            disabled={createTag.isPending}
            className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-50"
          >
            {createTag.isPending ? "Creating..." : "Create Tag"}
          </button>
        </form>
      )}

      <div className="space-y-2">
        {tagsData?.items.map((tag) => (
          <div
            key={tag.id}
            className="flex items-center justify-between border rounded-lg p-3"
          >
            {editingTag?.id === tag.id ? (
              <form
                onSubmit={editForm.handleSubmit(handleUpdate)}
                className="flex-1 flex items-center gap-2"
              >
                <input
                  {...editForm.register("name")}
                  className="flex-1 px-2 py-1 border rounded"
                />
                <input
                  {...editForm.register("color")}
                  type="color"
                  className="w-10 h-8 border rounded cursor-pointer"
                />
                <button
                  type="submit"
                  disabled={updateTag.isPending}
                  className="px-3 py-1 bg-primary text-primary-foreground rounded text-sm"
                >
                  Save
                </button>
                <button
                  type="button"
                  onClick={() => setEditingTag(null)}
                  className="px-3 py-1 border rounded text-sm"
                >
                  Cancel
                </button>
              </form>
            ) : (
              <>
                <div className="flex items-center gap-2">
                  {tag.color && (
                    <div
                      className="w-4 h-4 rounded"
                      style={{ backgroundColor: tag.color }}
                    />
                  )}
                  <span>{tag.name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleEdit(tag)}
                    className="p-1 hover:bg-gray-100 rounded"
                  >
                    <Pencil size={16} />
                  </button>
                  <button
                    onClick={() => handleDelete(tag.id)}
                    className="p-1 hover:bg-red-100 text-red-600 rounded"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </>
            )}
          </div>
        ))}
        {tagsData?.items.length === 0 && (
          <p className="text-center text-muted-foreground py-4">
            No tags yet. Create one to get started!
          </p>
        )}
      </div>
    </div>
  );
}
