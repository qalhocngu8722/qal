import { z } from "zod";

export const tagCreateSchema = z.object({
  name: z.string().min(1, "Name is required").max(50, "Name too long"),
  color: z.string().max(20).optional(),
});

export const tagUpdateSchema = z.object({
  name: z.string().min(1, "Name is required").max(50, "Name too long").optional(),
  color: z.string().max(20).optional(),
});

export type TagCreate = z.infer<typeof tagCreateSchema>;
export type TagUpdate = z.infer<typeof tagUpdateSchema>;
