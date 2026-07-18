import Link from "next/link";

export default function LoginPage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-20">
      <h1 className="text-3xl font-bold text-white">Login</h1>
      <p className="mt-4 text-slate-300">Authentication will be added in the identity and tenancy phase.</p>
      <Link className="mt-8 inline-block text-cyan-300 hover:text-cyan-200" href="/">Return home</Link>
    </main>
  );
}
