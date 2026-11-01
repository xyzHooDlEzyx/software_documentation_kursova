import { useEffect, useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router";

import { ApiError, login, register } from "../app/api";
import { useAuth } from "../app/auth/AuthProvider";
import { Alert, Button, TextInput } from "../components/ui";

type Props = { mode: "login" | "register" };
type LocationState = { from?: { pathname?: string }; registered?: boolean; loggedOut?: boolean };

export function AuthPage({ mode }: Props) {
  const navigate = useNavigate();
  const location = useLocation();
  const { setAccount } = useAuth();
  const state = location.state as LocationState | null;
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(state?.registered ? "Акаунт створено. Тепер увійдіть." : state?.loggedOut ? "Ви вийшли з акаунта." : "");
  const [fields, setFields] = useState<Record<string, string[]>>({});
  const [requestError, setRequestError] = useState("");

  useEffect(() => {
    setMessage(state?.registered ? "Акаунт створено. Тепер увійдіть." : state?.loggedOut ? "Ви вийшли з акаунта." : "");
  }, [location.key]);

  const isRegister = mode === "register";
  function errorText(error: unknown) {
    if (error instanceof ApiError) return error.message;
    return "Не вдалося виконати запит. Спробуйте ще раз.";
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFields({});
    setMessage("");
    setRequestError("");
    const nextFields: Record<string, string[]> = {};
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) nextFields.email = ["Введіть коректну email-адресу."];
    if (!password) nextFields.password = ["Введіть пароль."];
    else if (isRegister && password.length < 12) nextFields.password = ["Пароль має містити щонайменше 12 символів."];
    if (Object.keys(nextFields).length) { setFields(nextFields); return; }

    setBusy(true);
    try {
      if (isRegister) {
        await register(email.trim(), password);
        navigate("/login", { replace: true, state: { registered: true } });
      } else {
        const account = await login(email.trim(), password);
        setAccount(account);
        setPassword("");
        navigate(state?.from?.pathname || "/", { replace: true });
      }
    } catch (error) {
      if (error instanceof ApiError) setFields(error.fields);
      setRequestError(errorText(error));
    } finally { setBusy(false); }
  }

  return (
    <div className="grid gap-space-5">
      <div className="grid gap-space-2">
        <p className="m-0 text-caption font-bold uppercase tracking-[0.08em] text-brand-secondary-token">Особистий кабінет</p>
        <h1 className="m-0 text-title-large font-bold leading-[var(--line-height-title-large)] tracking-[var(--letter-spacing-heading)] text-foreground">
          {isRegister ? "Створити акаунт" : "З поверненням"}
        </h1>
        <p className="m-0 text-body text-muted-foreground">
          {isRegister ? "Зареєструйтеся, щоб зберігати власні тренування та прогрес." : "Увійдіть, щоб продовжити роботу зі своїм акаунтом."}
        </p>
      </div>
      {message && <Alert tone="success">{message}</Alert>}
      {requestError && <Alert tone="error">{requestError}</Alert>}
      <form className="grid gap-space-4" onSubmit={(event) => void submit(event)} noValidate>
        <TextInput id="email" label="Email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} error={fields.email?.join(" ")} />
        <TextInput id="password" label="Пароль" type="password" autoComplete={isRegister ? "new-password" : "current-password"} value={password} onChange={(event) => setPassword(event.target.value)} error={fields.password?.join(" ")} hint={isRegister ? "Щонайменше 12 символів." : undefined} />
        {!isRegister && (
          <div className="flex justify-end">
            <Link className="text-small font-semibold text-brand underline-offset-4 hover:underline" to="/forgot-password">
              Забули пароль?
            </Link>
          </div>
        )}
        <Button type="submit" loading={busy} className="mt-space-1 w-full">{isRegister ? "Створити акаунт" : "Увійти"}</Button>
      </form>
      <p className="m-0 text-center text-small text-muted-foreground">
        {isRegister ? "Вже маєте акаунт? " : "Ще не маєте акаунта? "}
        <Link className="font-semibold text-brand underline-offset-4 hover:underline" to={isRegister ? "/login" : "/register"}>{isRegister ? "Увійти" : "Зареєструватися"}</Link>
      </p>
    </div>
  );
}
