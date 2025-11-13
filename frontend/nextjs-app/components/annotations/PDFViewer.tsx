'use client';

import { useState } from 'react';

interface PDFViewerProps {
  paperId?: number;
  pdfUrl?: string;
  title?: string;
  content?: string;
}

export default function PDFViewer({ paperId, pdfUrl, title = 'Document', content }: PDFViewerProps) {
  const [zoom, setZoom] = useState(100);
  const [loadError, setLoadError] = useState(false);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  // Determine the PDF URL to use
  const effectivePdfUrl = pdfUrl || (paperId ? `${API_URL}/api/v1/papers/${paperId}/pdf` : null);

  const handleZoom = (direction: 'in' | 'out') => {
    setZoom((prev) => {
      if (direction === 'in') return Math.min(prev + 10, 200);
      return Math.max(prev - 10, 50);
    });
  };

  // If we have a PDF URL, show the PDF viewer
  if (effectivePdfUrl && !loadError) {
    return (
      <div className="flex-1 flex flex-col bg-gray-100 dark:bg-gray-900 relative">
        {/* Zoom Controls */}
        <div className="absolute top-4 right-4 z-10 flex gap-2">
          <button
            onClick={() => handleZoom('out')}
            className="bg-white dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 px-3 py-2 rounded shadow-md"
            title="Zoom out"
          >
            <span className="material-symbols-outlined">zoom_out</span>
          </button>
          <span className="bg-white dark:bg-gray-800 px-3 py-2 rounded shadow-md text-gray-700 dark:text-gray-200">
            {zoom}%
          </span>
          <button
            onClick={() => handleZoom('in')}
            className="bg-white dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 px-3 py-2 rounded shadow-md"
            title="Zoom in"
          >
            <span className="material-symbols-outlined">zoom_in</span>
          </button>
        </div>

        {/* PDF Iframe */}
        <iframe
          src={`${effectivePdfUrl}#zoom=${zoom}`}
          className="w-full h-full border-0"
          title={title}
          onError={() => setLoadError(true)}
        />
      </div>
    );
  }

  // Fallback to text content view if PDF not available
  const sampleContent = content || `
    The field of artificial intelligence (AI) has seen exponential growth over the past decade,
    revolutionizing industries from healthcare to finance. This paper explores the trajectory of AI,
    examining its potential impacts on society, ethics, and the future of work. We delve into the
    current state of AI research, focusing on advancements in machine learning, natural language
    processing, and computer vision.

    One of the most significant areas of development is deep learning, a subset of machine learning
    based on artificial neural networks. The ability of these networks to learn from vast amounts of
    data has led to breakthroughs in tasks that were once considered exclusively human domains.

    However, the rapid advancement of AI also raises critical ethical questions. Ensuring fairness,
    accountability, and transparency in AI systems is paramount. Without proper governance, we risk
    perpetuating and even amplifying existing societal biases. The development of 'explainable AI'
    (XAI) is a step in the right direction, aiming to make the decision-making processes of AI models
    more understandable to humans.

    The societal impact of AI cannot be overstated. From autonomous vehicles to personalized medicine,
    the potential benefits are immense. This paper will explore both the utopian and dystopian scenarios,
    providing a balanced perspective on what the future may hold. As we move forward, a multidisciplinary
    approach involving technologists, ethicists, policymakers, and the public will be crucial in shaping
    a future where AI serves humanity as a whole.

    Further research should focus on creating robust AI systems that are resilient to adversarial attacks.
    The security of AI is a growing concern, as malicious actors could potentially exploit vulnerabilities
    in these complex systems.
  `;

  return (
    <main className="flex-1 overflow-y-auto bg-white dark:bg-gray-900/50 p-8 relative">
      <div className="max-w-4xl mx-auto" style={{ fontSize: `${zoom}%` }}>
        {loadError && (
          <div className="mb-4 p-4 bg-yellow-100 dark:bg-yellow-900/30 border border-yellow-300 dark:border-yellow-700 rounded">
            <p className="text-yellow-800 dark:text-yellow-200">
              Unable to load PDF. Showing text content instead.
            </p>
          </div>
        )}

        {/* Document Content */}
        <div className="space-y-6 font-body text-lg leading-relaxed text-gray-800 dark:text-gray-300">
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white mt-4">{title}</h2>
          <p className="text-gray-600 dark:text-gray-400">Abstract</p>

          {sampleContent.split('\n\n').map((paragraph, index) => (
            <p key={index} className="whitespace-pre-wrap">
              {paragraph.trim()}
            </p>
          ))}
        </div>
      </div>
    </main>
  );
}
