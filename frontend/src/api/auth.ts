import { useQuery, useMutation } from "@tanstack/react-query";
import client from "./client";

export function useLogin() {
  return useMutation({
    mutationFn: (data: { username: string; password: string }) =>
      client.post<{ token: string; user_id: number }>("/auth/login/", data).then((r) => r.data),
  });
}

export function useRegister() {
  return useMutation({
    mutationFn: (data: { username: string; email: string; password: string }) =>
      client.post<{ token: string; user_id: number }>("/auth/register/", data).then((r) => r.data),
  });
}

export function useProfile() {
  return useQuery({
    queryKey: ["profile"],
    queryFn: () => client.get("/auth/profile/").then((r) => r.data),
  });
}
