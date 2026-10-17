import { redirect } from "next/navigation";
import { RESERVOIR_HREF } from "@/lib/site-scope";
export default function HomePage() {
  redirect(RESERVOIR_HREF);
}
