"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/auth";

export default function RootPage() {
  const router = useRouter();
  useEffect(() => {
    if (getToken()) router.replace("/chat/new");
    else router.replace("/login");
  }, [router]);
  return null;
}
