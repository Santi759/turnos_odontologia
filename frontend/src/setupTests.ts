import { cleanup } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";

// Sin `globals`, Testing Library no limpia el DOM solo entre pruebas.
afterEach(() => {
  cleanup();
});
