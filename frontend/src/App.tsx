import { BrowserRouter } from "react-router";

import { AuthProvider } from "./app/auth/AuthProvider";
import { AppRouter } from "./app/router/AppRouter";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRouter />
      </AuthProvider>
    </BrowserRouter>
  );
}
