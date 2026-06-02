"use client";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

// Redirect to a stable ID for new chats — just use "session" as a transient placeholder
export default function NewChatPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/chat/session");
  }, [router]);
  return null;
}
