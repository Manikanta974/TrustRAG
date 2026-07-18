import Link from "next/link";

const routes = [
  { href: "/login", label: "Login" },
  { href: "/chat", label: "Chat" },
  { href: "/knowledge-base", label: "Knowledge base" },
  { href: "/admin", label: "Admin" },
];

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col justify-center px-6 py-16">
      <p className="mb-4 text-sm font-semibold uppercase tracking-[0.2em] text-cyan-300">TrustRAG</p>
      <h1 className="max-w-3xl text-4xl font-bold tracking-tight text-white sm:text-6xl">
        Secure Enterprise RAG Platform
      </h1>
      <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300">
        Permission-aware internal document intelligence with grounded, citation-backed answers.
      </p>
      <nav aria-label="Planned application areas" className="mt-10 flex flex-wrap gap-3">
        {routes.map((route) => (
          <Link
            className="rounded-md border border-slate-700 px-4 py-2 text-sm font-medium text-slate-100 transition hover:border-cyan-300 hover:text-cyan-200"
            href={route.href}
            key={route.href}
          >
            {route.label}
          </Link>
        ))}
      </nav>
    </main>
  );
}
