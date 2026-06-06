import { useState } from "react";
import { X } from "lucide-react";
import { useTags } from "@/features/tags/api/tags";

interface TodoFiltersProps {
  filters: {
    status?: "active" | "completed";
    tag_id?: string;
    keyword?: string;
    date_from?: string;
    date_to?: string;
  };
  onFilterChange: (filters: any) => void;
}

export function TodoFilters({ filters, onFilterChange }: TodoFiltersProps) {
  const { data: tagsData } = useTags();
  const [keyword, setKeyword] = useState(filters.keyword || "");

  const handleClearFilters = () => {
    setKeyword("");
    onFilterChange({});
  };

  const hasActiveFilters =
    filters.status || filters.tag_id || filters.keyword || filters.date_from || filters.date_to;

  return (
    <div className="space-y-3 border rounded-lg p-4 bg-gray-50">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">Filters</h3>
        {hasActiveFilters && (
          <button
            onClick={handleClearFilters}
            className="text-sm text-primary hover:underline inline-flex items-center gap-1"
          >
            <X size={14} />
            Clear all
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Keyword search */}
        <div>
          <label className="block text-sm font-medium mb-1">Search</label>
          <input
            type="text"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                onFilterChange({ ...filters, keyword: keyword || undefined });
              }
            }}
            onBlur={() => {
              onFilterChange({ ...filters, keyword: keyword || undefined });
            }}
            placeholder="Search todos..."
            className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>

        {/* Status filter */}
        <div>
          <label className="block text-sm font-medium mb-1">Status</label>
          <select
            value={filters.status || ""}
            onChange={(e) =>
              onFilterChange({
                ...filters,
                status: e.target.value || undefined,
              })
            }
            className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="">All</option>
            <option value="active">Active</option>
            <option value="completed">Completed</option>
          </select>
        </div>

        {/* Tag filter */}
        <div>
          <label className="block text-sm font-medium mb-1">Tag</label>
          <select
            value={filters.tag_id || ""}
            onChange={(e) =>
              onFilterChange({
                ...filters,
                tag_id: e.target.value || undefined,
              })
            }
            className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="">All tags</option>
            {tagsData?.items.map((tag) => (
              <option key={tag.id} value={tag.id}>
                {tag.name}
              </option>
            ))}
          </select>
        </div>

        {/* Date from */}
        <div>
          <label className="block text-sm font-medium mb-1">From date</label>
          <input
            type="date"
            value={filters.date_from || ""}
            onChange={(e) =>
              onFilterChange({
                ...filters,
                date_from: e.target.value || undefined,
              })
            }
            className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>

        {/* Date to */}
        <div>
          <label className="block text-sm font-medium mb-1">To date</label>
          <input
            type="date"
            value={filters.date_to || ""}
            onChange={(e) =>
              onFilterChange({
                ...filters,
                date_to: e.target.value || undefined,
              })
            }
            className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
      </div>
    </div>
  );
}
