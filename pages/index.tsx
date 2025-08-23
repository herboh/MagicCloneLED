// pages/index.tsx
import Head from "next/head";
import { BulbControls } from "../components/controls/BulbControls";

export default function Home() {
  return (
    <div className="min-h-screen" style={{ background: "#1d2021" }}>
      <Head>
        <title>LED Controller</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <BulbControls />
    </div>
  );
}

