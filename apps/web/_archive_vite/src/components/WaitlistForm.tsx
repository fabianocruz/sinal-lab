import { useState } from "react";
import { submitWaitlist } from "../lib/api";
import Button from "./Button";

/**
 * Waitlist signup form component.
 *
 * Provides an interactive form for users to join the founding member waitlist.
 * Handles email validation, API submission, loading states, and success/error feedback.
 * On successful signup, displays confirmation with the user's position in the queue.
 *
 * @component
 *
 * @example
 * ```tsx
 * <WaitlistForm />
 * ```
 *
 * States:
 * - idle: Initial state, form ready for input
 * - loading: Submitting data to API
 * - success: Successfully registered, shows confirmation
 * - error: Validation or API error, shows error message
 */
export default function WaitlistForm() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [position, setPosition] = useState<number | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!email || !email.includes("@")) {
      setErrorMessage("Por favor, insira um email válido");
      setStatus("error");
      return;
    }

    setStatus("loading");
    setErrorMessage("");

    try {
      const response = await submitWaitlist({ email });
      setStatus("success");
      setPosition(response.position || null);
      setEmail("");
    } catch (error) {
      setStatus("error");
      setErrorMessage(
        error instanceof Error ? error.message : "Erro ao cadastrar. Tente novamente.",
      );
    }
  };

  if (status === "success") {
    return (
      <div className="bg-green-50 border-2 border-green-200 rounded-lg p-6 text-center">
        <div className="text-2xl mb-2">✅</div>
        <h3 className="font-bold text-lg mb-2">Você está na lista!</h3>
        <p className="text-gray-700 mb-2">
          Confirmação enviada para <span className="font-semibold">{email || "seu email"}</span>
        </p>
        {position && (
          <p className="text-sm text-gray-600">
            Posição na fila: <span className="font-semibold">#{position}</span>
          </p>
        )}
        <button
          onClick={() => {
            setStatus("idle");
            setPosition(null);
          }}
          className="mt-4 text-sm text-red-600 hover:text-red-700 underline"
        >
          Cadastrar outro email
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-lg mx-auto">
      <div className="flex flex-col md:flex-row gap-3">
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="seu@email.com"
          className="flex-1 px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-red-600 focus:outline-none"
          disabled={status === "loading"}
          required
        />
        <Button variant="primary" size="md" onClick={handleSubmit} className="whitespace-nowrap">
          {status === "loading" ? "Enviando..." : "Assinar grátis"}
        </Button>
      </div>

      {status === "error" && errorMessage && (
        <p className="mt-3 text-sm text-red-600 text-center">{errorMessage}</p>
      )}

      <p className="mt-3 text-xs text-gray-500 text-center">
        Sem spam. Cancele quando quiser. 100% gratuito.
      </p>
    </form>
  );
}
