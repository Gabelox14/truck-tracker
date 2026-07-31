import { supabase } from "./supabaseClient";

export async function uploadVinPhoto(file) {
  const ext = file.name.split(".").pop();
  const path = `${crypto.randomUUID()}.${ext}`;
  const { error } = await supabase.storage.from("truck-photos").upload(path, file);
  if (error) throw error;
  const { data } = supabase.storage.from("truck-photos").getPublicUrl(path);
  return data.publicUrl;
}
