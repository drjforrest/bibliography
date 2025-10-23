'use client';

import { useState } from 'react';

interface PDFViewerProps {
  content?: string;
  title?: string;
}

export default function PDFViewer({ content, title = 'Document' }: PDFViewerProps) {
  const [zoom, setZoom] = useState(100);

  // Sample content for demonstration
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

  const handleZoom = (direction: 'in' | 'out') => {
    setZoom((prev) => {
      if (direction === 'in') return Math.min(prev + 10, 200);
      return Math.max(prev - 10, 50);
    });
  };

  return (
    <main className="flex-1 overflow-y-auto bg-white dark:bg-gray-900/50 p-8 relative">
      <div className="max-w-4xl mx-auto" style={{ fontSize: `${zoom}%` }}>
        {/* Document Content */}
        <div className="space-y-6 font-body text-lg leading-relaxed text-gray-800 dark:text-gray-300">
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white mt-4">{title}</h2>
          <p className="text-gray-600 dark:text-gray-400">Chapter 1: Introduction</p>

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
