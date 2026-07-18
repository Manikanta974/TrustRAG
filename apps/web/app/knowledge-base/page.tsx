import Link from "next/link";

export default function KnowledgeBasePage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-20">
      <h1 className="text-3xl font-bold text-white">Knowledge base</h1>
      <p className="mt-4 text-slate-300">Secure document ingestion and indexing are planned for a later phase.</p>
      <Link className="mt-8 inline-block text-cyan-300 hover:text-cyan-200" href="/">Return home</Link>
    </main>
  );
}
