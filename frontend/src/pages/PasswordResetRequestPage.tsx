import { useState, type FormEvent } from "react";
import { Link } from "react-router";

import { ApiError, requestPasswordReset } from "../app/api";
import { Alert, Button, TextInput } from "../components/ui";

const DEFAULT_SUCCESS_MESSAGE =
  "Якщо акаунт із такою адресою існує, ми надішлемо інструкції для відновлення пароля.";

export function PasswordResetRequestPage() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [fields, setFields] = useState<Record<string, string[]>>({});
  const [requestError, setRequestError] = useState("");

  function errorText(error: unknown) {
    if (error instanceof ApiError) return error.message;
    return "Не вдалося виконати запит. Спробуйте ще раз.";
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFields({});
    setSuccessMessage("");
    setRequestError("");

    const trimmedEmail = email.trim();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      setFields({ email: ["Введіть коректну email-адресу."] });
      return;
    }

    setBusy(true);
    try {
      const response = await requestPasswordReset(trimmedEmail);
      setSubmitted(true);
      setSuccessMessage(response.message || DEFAULT_SUCCESS_MESSAGE);
    } catch (error) {
      if (error instanceof ApiError) {
        setFields(error.fields);
      }
      setRequestError(errorText(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-space-5">
      <div className="grid gap-space-2">
        <p className="m-0 text-caption font-bold uppercase tracking-[0.08em] text-brand-secondary-token">
          Особистий кабінет
        </p>
        <h1 className="m-0 text-title-large font-bold leading-[var(--line-height-title-large)] tracking-[var(--letter-spacing-heading)] text-foreground">
          Відновлення пароля
        </h1>
        <p className="m-0 text-body text-muted-foreground">
          Вкажіть електронну пошту, пов’язану з вашим акаунтом.
        </p>
      </div>
      {successMessage && <Alert tone="success">{successMessage}</Alert>}
      {requestError && <Alert tone="error">{requestError}</Alert>}
      <form className="grid gap-space-4" onSubmit={(event) => void submit(event)} noValidate>
        <TextInput
          id="email"
          label="Електронна пошта"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          error={fields.email?.join(" ")}
          hint="Ми надішлемо захищене посилання для створення нового пароля."
        />
        <Button type="submit" loading={busy} className="mt-space-1 w-full">
          {submitted ? "Надіслати повторно" : "Надіслати інструкції"}
        </Button>
      </form>
      <p className="m-0 text-center text-small text-muted-foreground">
        <Link className="font-semibold text-brand underline-offset-4 hover:underline" to="/login">
          Повернутися до входу
        </Link>
      </p>
    </div>
  );
}
