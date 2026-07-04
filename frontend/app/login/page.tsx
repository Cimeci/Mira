import { Suspense } from "react";
import { GlowBackdrop } from "@/components/ui/GlowBackdrop";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { LoginForm } from "@/components/auth/LoginForm";

export default function LoginScreen() {
  return (
    <div className="relative mx-auto flex min-h-screen w-full max-w-[1440px] flex-col items-center overflow-hidden bg-mira-void">
      <GlowBackdrop />
      <Header />

      <main className="mt-auto w-full max-w-[440px] px-5 sm:px-0">
        {/* useSearchParams (next=…) requires a Suspense boundary in app router */}
        <Suspense fallback={null}>
          <LoginForm />
        </Suspense>
      </main>

      <Footer>your session is private — cases are only visible to you.</Footer>
    </div>
  );
}
