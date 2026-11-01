import { useEffect, useState, type FormEvent } from "react";

import {
  ApiError,
  currentUser,
  initializeCsrf,
  login,
  logout,
  register,
  updateLeaderboard,
  type Account,
} from "./app/api";

type Mode = "login" | "register";

function errorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  return "Не вдалося виконати запит. Спробуйте ще раз.";
}

export default function App() {
  const [account, setAccount] = useState<Account | null>(null);
  const [booting, setBooting] = useState(true);
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [alias, setAlias] = useState("");
  const [optIn, setOptIn] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [fields, setFields] = useState<Record<string, string[]>>({});

  useEffect(() => {
    let active = true;
    async function bootstrap() {
      try {
        await initializeCsrf();
        const user = await currentUser();
        if (active) {
          setAccount(user);
          setAlias(user.public_alias ?? "");
          setOptIn(user.leaderboard_opt_in);
        }
      } catch (error) {
        if (active && !(error instanceof ApiError && error.status === 401)) {
          setMessage(errorMessage(error));
        }
      } finally {
        if (active) setBooting(false);
      }
    }
    void bootstrap();
    return () => { active = false; };
  }, []);

  function showError(error: unknown) {
    if (error instanceof ApiError) {
      setFields(error.fields);
      if (error.status === 401 && account) setAccount(null);
    }
    setMessage(errorMessage(error));
  }

  async function submitAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFields({});
    setMessage("");
    const errors: Record<string, string[]> = {};
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      errors.email = ["Введіть коректну email-адресу."];
    }
    if (!password) errors.password = ["Введіть пароль."];
    else if (mode === "register" && password.length < 12) {
      errors.password = ["Пароль має містити щонайменше 12 символів."];
    }
    if (Object.keys(errors).length) {
      setFields(errors);
      return;
    }
    setBusy(true);
    try {
      if (mode === "register") {
        await register(email.trim(), password);
        setMode("login");
        setPassword("");
        setMessage("Акаунт створено. Тепер увійдіть.");
      } else {
        const user = await login(email.trim(), password);
        setAccount(user);
        setAlias(user.public_alias ?? "");
        setOptIn(user.leaderboard_opt_in);
        setPassword("");
      }
    } catch (error) {
      showError(error);
    } finally {
      setBusy(false);
    }
  }

  async function submitLogout() {
    setBusy(true);
    setMessage("");
    try {
      await logout();
      setAccount(null);
      setPassword("");
      setMessage("Ви вийшли з акаунта.");
    } catch (error) {
      showError(error);
    } finally {
      setBusy(false);
    }
  }

  async function submitSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFields({});
    setMessage("");
    setBusy(true);
    try {
      const user = await updateLeaderboard(alias.trim() || null, optIn);
      setAccount(user);
      setMessage("Налаштування рейтингу збережено.");
    } catch (error) {
      showError(error);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="shell">
      <div className="card">
        <p className="eyebrow">Курсова робота · Варіант 4</p>
        <h1>Фітнес-трекер</h1>
        {booting ? <p role="status">Перевіряємо сесію…</p> : account ? (
          <>
            <p>Ви увійшли як <strong>{account.email}</strong>.</p>
            <form onSubmit={(event) => void submitSettings(event)}>
              <h2>Публічний рейтинг</h2>
              <label htmlFor="public-alias">Псевдонім</label>
              <input id="public-alias" value={alias} maxLength={80} onChange={(event) => setAlias(event.target.value)} />
              {fields.public_alias && <p className="field-error">{fields.public_alias.join(" ")}</p>}
              <label className="check-label" htmlFor="leaderboard-opt-in">
                <input id="leaderboard-opt-in" type="checkbox" checked={optIn} onChange={(event) => setOptIn(event.target.checked)} />
                Показувати мене в рейтингу
              </label>
              <button disabled={busy} type="submit">Зберегти</button>
            </form>
            <button className="secondary" disabled={busy} onClick={() => void submitLogout()} type="button">Вийти</button>
          </>
        ) : (
          <>
            <div className="tabs" aria-label="Акаунт">
              <button type="button" aria-pressed={mode === "login"} onClick={() => { setMode("login"); setFields({}); setMessage(""); }}>Вхід</button>
              <button type="button" aria-pressed={mode === "register"} onClick={() => { setMode("register"); setFields({}); setMessage(""); }}>Реєстрація</button>
            </div>
            <form onSubmit={(event) => void submitAuth(event)} noValidate>
              <label htmlFor="email">Email</label>
              <input id="email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} />
              {fields.email && <p className="field-error">{fields.email.join(" ")}</p>}
              <label htmlFor="password">Пароль</label>
              <input id="password" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} value={password} onChange={(event) => setPassword(event.target.value)} />
              {fields.password && <p className="field-error">{fields.password.join(" ")}</p>}
              <button disabled={busy} type="submit">{busy ? "Зачекайте…" : mode === "login" ? "Увійти" : "Створити акаунт"}</button>
            </form>
          </>
        )}
        {message && <p role="status" className="message">{message}</p>}
      </div>
    </main>
  );
}
