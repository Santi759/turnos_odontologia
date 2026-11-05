import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "./App";

describe("App", () => {
  it("renderiza el encabezado principal con el texto exacto", () => {
    render(<App />);

    const encabezado = screen.getByRole("heading", { level: 1 });

    expect(encabezado).toHaveTextContent(/^Turnos Odontología$/);
  });

  it("tiene un unico encabezado principal", () => {
    render(<App />);

    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });
});
