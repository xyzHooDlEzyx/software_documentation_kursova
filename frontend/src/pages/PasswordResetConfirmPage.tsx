import { useLayoutEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router";

import { ApiError, confirmPasswordReset } from "../app/api";
import { useAuth } from "../app/auth/AuthProvider";
import { Alert, Button, TextInput, buttonVariants } from "../components/ui";

type ResetCredentials = {
  uid: string;
  token: string;
};

type HistoryResetState = {
  resetCredentials?: ResetCredentials;
};

let activeResetCredentials: ResetCredentials | null = null;

export function clearResetCredentialsMemory() {
  activeResetCredentials = null;
  if (typeof window !== "undefined") {
    const state = window.history.state as HistoryResetState | null;
    if (state?.resetCredentials) {
      window.history.replaceState(null, "", "/reset-password");
    }
  }
}

function readHistoryCredentials(): ResetCredentials | null {
  if (typeof window === "undefined") return null;
  const state = window.history.state as HistoryResetState | null;
  const creds = state?.resetCredentials;
  if (
    creds &&
    typeof creds.uid === "string" &&
    creds.uid.trim().length > 0 &&
    typeof creds.token === "string" &&
    creds.token.trim().length > 0
  ) {
    return { uid: creds.uid, token: creds.token };
  }
  return null;
}

function resolveInitialCredentials(paramUid?: string, paramToken?: string): ResetCredentials | null {
  if (paramUid && paramToken) {
    const next = { uid: paramUid, token: paramToken };
    activeResetCredentials = next;
    return next;
  }
  const fromHistory = readHistoryCredentials();
  if (fromHistory) {
    activeResetCredentials = fromHistory;
    return fromHistory;
  }
  if (activeResetCredentials) {
    return activeResetCredentials;
  }
  return null;
}

const DEFAULT_INVALID_LINK_MESSAGE = "Термін дії посилання вичерпано або посилання недійсне.";
const DEFAULT_SUCCESS_MESSAGE = "Пароль оновлено. Увійдіть із новим паролем.";

export function PasswordResetConfirmPage() {
  const params = useParams<{ uid?: string; token?: string }>();
  const { setAccount } = useAuth();

  const [credentials, setCredentials] = useState<ResetCredentials | null>(() =>
    resolveInitialCredentials(params.uid, params.token),
  );
  const [invalidLinkMessage, setInvalidLinkMessage] = useState<string>(() =>
    resolveInitialCredentials(params.uid, params.token) ? "" : DEFAULT_INVALID_LINK_MESSAGE,
  );
  const [successMessage, setSuccessMessage] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [fields, setFields] = useState<Record<string, string[]>>({});
  const [requestError, setRequestError] = useState("");

  useLayoutEffect(() => {
    if (params.uid && params.token) {
      const next = { uid: params.uid, token: params.token };
      activeResetCredentials = next;
      setCredentials(next);
      setInvalidLinkMessage("");
      window.history.replaceState({ resetCredentials: next }, "", "/reset-password");
      return;
    }

    const existing = readHistoryCredentials() ?? activeResetCredentials;
    if (!existing) {
      clearResetCredentialsMemory();
      setCredentials(null);
      setInvalidLinkMessage((prev) => prev || DEFAULT_INVALID_LINK_MESSAGE);
    }
  }, [params.uid, params.token]);

  function errorText(error: unknown) {
    if (error instanceof ApiError) return error.message;
    return "Не вдалося виконати запит. Спробуйте ще раз.";
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFields({});
    setRequestError("");

    if (!credentials) {
      clearResetCredentialsMemory();
      setInvalidLinkMessage(DEFAULT_INVALID_LINK_MESSAGE);
      return;
    }

    const nextFields: Record<string, string[]> = {};
    if (!newPassword) {
      nextFields.new_password = ["Введіть новий пароль."];
    } else if (newPassword.length < 12) {
      nextFields.new_password = ["Пароль має містити щонайменше 12 символів."];
    }

    if (!confirmPassword) {
      nextFields.confirm_password = ["Підтвердіть новий пароль."];
    } else if (newPassword !== confirmPassword) {
      nextFields.confirm_password = ["Паролі не співпадають."];
    }

    if (Object.keys(nextFields).length > 0) {
      setFields(nextFields);
      return;
    }

    setBusy(true);
    try {
      const response = await confirmPasswordReset(credentials.uid, credentials.token, newPassword);
      clearResetCredentialsMemory();
      setCredentials(null);
      setNewPassword("");
      setConfirmPassword("");
      setAccount(null);
      setSuccessMessage(response.message || DEFAULT_SUCCESS_MESSAGE);
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.code === "reset_token_invalid_or_expired") {
          clearResetCredentialsMemory();
          setCredentials(null);
          setNewPassword("");
          setConfirmPassword("");
          const detail =
            error.message && error.message !== DEFAULT_INVALID_LINK_MESSAGE
              ? `${DEFAULT_INVALID_LINK_MESSAGE} ${error.message}`
              : DEFAULT_INVALID_LINK_MESSAGE;
          setInvalidLinkMessage(detail);
          return;
        }
        setFields(error.fields);
      }
      setRequestError(errorText(error));
    } finally {
      setBusy(false);
    }
  }

  if (successMessage) {
    return (
      <div className="grid gap-space-5">
        <div className="grid gap-space-2">
          <p className="m-0 text-caption font-bold uppercase tracking-[0.08em] text-brand-secondary-token">
            Безпечне скидання
          </p>
          <h1 className="m-0 text-title-large font-bold leading-[var(--line-height-title-large)] tracking-[var(--letter-spacing-heading)] text-foreground">
            Пароль оновлено
          </h1>
        </div>
        <Alert tone="success">{successMessage}</Alert>
        <Link className={buttonVariants({ variant: "primary", className: "w-full" })} to="/login">
          Перейти до входу
        </Link>
      </div>
    );
  }

  if (invalidLinkMessage || !credentials) {
    return (
      <div className="grid gap-space-5">
        <div className="grid gap-space-2">
          <p className="m-0 text-caption font-bold uppercase tracking-[0.08em] text-brand-secondary-token">
            Безпечне скидання
          </p>
          <h1 className="m-0 text-title-large font-bold leading-[var(--line-height-title-large)] tracking-[var(--letter-spacing-heading)] text-foreground">
            Посилання недійсне
          </h1>
        </div>
        <Alert tone="error">{invalidLinkMessage || DEFAULT_INVALID_LINK_MESSAGE}</Alert>
        <Link className={buttonVariants({ variant: "primary", className: "w-full" })} to="/forgot-password">
          Запросити нове посилання
        </Link>
        <p className="m-0 text-center text-small text-muted-foreground">
          <Link className="font-semibold text-brand underline-offset-4 hover:underline" to="/login">
            Повернутися до входу
          </Link>
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-space-5">
      <div className="grid gap-space-2">
        <p className="m-0 text-caption font-bold uppercase tracking-[0.08em] text-brand-secondary-token">
          Безпечне скидання
        </p>
        <h1 className="m-0 text-title-large font-bold leading-[var(--line-height-title-large)] tracking-[var(--letter-spacing-heading)] text-foreground">
          Встановлення нового пароля
        </h1>
        <p className="m-0 text-body text-muted-foreground">
          Введіть новий надійний пароль для вашого облікового запису.
        </p>
      </div>
      {requestError && <Alert tone="error">{requestError}</Alert>}
      <form className="grid gap-space-4" onSubmit={(event) => void submit(event)} noValidate>
        <TextInput
          id="new-password"
          label="Новий пароль"
          type="password"
          autoComplete="new-password"
          value={newPassword}
          onChange={(event) => setNewPassword(event.target.value)}
          error={fields.new_password?.join(" ")}
          hint="Щонайменше 12 символів."
        />
        <TextInput
          id="confirm-password"
          label="Підтвердження нового пароля"
          type="password"
          autoComplete="new-password"
          value={confirmPassword}
          onChange={(event) => setConfirmPassword(event.target.value)}
          error={fields.confirm_password?.join(" ")}
        />
        <Button type="submit" loading={busy} className="mt-space-1 w-full">
          Зберегти новий пароль
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
