'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import ProtectedRoute from '@/components/ProtectedRoute';
import Header from '@/components/layout/Header';
import AnnotationToolbar from '@/components/annotations/AnnotationToolbar';
import PDFViewer from '@/components/annotations/PDFViewer';
import AnnotationSidebar from '@/components/annotations/AnnotationSidebar';
import type { Annotation, AnnotationType } from '@/types';

// Mock annotations data
const mockAnnotations: Annotation[] = [
  {
    id: '1',
    paperId: '1',
    userId: 'user1',
    user: {
      id: 'user1',
      name: 'Jane Doe',
      email: 'jane@example.com',
      avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuC__aKnC-IsI1UJtLXNk_iYpj-kfCZkB3TBmd5_4OIlZ2jncZa3tP0DWxjmXFUpKJ5TVmUHHV8Z8dEqPN-m6SP-6B8d2dnbczlTHm0DPgUnLPOtz07buMKZIg3beheyT3spnHDBVMpE5tImxC4XEwSZosWdmtNPZf6ZhoDbaQ-Zl43i9VtHsOkZ36pGLk5vdAB_Mrze8bmG6b-jyqL9dZ_sRsV6UI53gorCjPV555b-7jXWR1WSAq3kFrv73WwyyRd8mlYIKfTgTdSw',
    },
    type: 'highlight',
    content: 'This definition is a bit simplistic. We should elaborate on the specific architectures like CNNs and RNNs.',
    quote: 'deep learning, a subset of machine learning based on artificial neural networks.',
    page: 1,
    createdAt: new Date(Date.now() - 86400000), // 1 day ago
    isPrivate: false,
  },
  {
    id: '2',
    paperId: '1',
    userId: 'user2',
    user: {
      id: 'user2',
      name: 'Alex Smith',
      email: 'alex@example.com',
      avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAj4A6l0NKfALi5NVTkWgRPRNUz2K9uKYbGME-ph0fV2ZDUx5tYAwFGmSHD_8OP7AnDB1By4zCT4CFiCY4UsWNRFTBE_5xTAA0o9YrExoPq5uaXFf1udpGrdpStxWWs4OFU5T7r3PtnJXaLVmqU_03Ph8HkI49aBmfyjVnL0wdcd-7Xhl8iVs5QDFtZsKjC-76GKtB-okaKv3q3AGaEZkpGi3gjZRbJ2RAZDQx9gmvIBz2rTfJ4FcBV7wOKfpneduPsp0YRHajISGmp',
    },
    type: 'underline',
    content: '',
    quote: 'Ensuring fairness, accountability, and transparency in AI systems is paramount.',
    page: 1,
    createdAt: new Date(Date.now() - 86400000),
    isPrivate: false,
  },
  {
    id: '3',
    paperId: '1',
    userId: 'user3',
    user: {
      id: 'user3',
      name: 'Emily Carter',
      email: 'emily@example.com',
      avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuD1GnqLAmYba4zXy8osZ4SB2D-8C3VW_4nluH3Ny-awtqwk1SKyIWjsvhgd8HwuRGbk-FylZIg0x_mBy2DcLS_X0X5f_a9IKdBt7Eqpfz9L-Xc3NrJfoieXYkSamiVSpu2xXhLR809Wmljmos9DqPX-VvaHgKQYZrsCYNQuyi8DUQ4z0-xs4rnWsvVHiTZQgWI3nQYlf2O70lc_4g2Aiaus4FRo-LuvtmC9gVb1dxnxp6wjgYz0oXGYN1q_YUiK4xu2190m0A3aTKHH',
    },
    type: 'comment',
    content: 'This is a critical point. We should also consider the economic displacement that will result from increased automation.',
    quote: 'potential benefits are immense.',
    page: 1,
    createdAt: new Date(Date.now() - 172800000), // 2 days ago
    isPrivate: false,
  },
];

export default function PaperAnnotationPage() {
  const params = useParams();
  const paperId = params.paperId as string;
  const [annotations, setAnnotations] = useState<Annotation[]>(mockAnnotations);
  const [activeTool, setActiveTool] = useState<AnnotationType | null>(null);

  const handleToolSelect = (tool: AnnotationType | 'zoom_in' | 'zoom_out') => {
    if (tool === 'zoom_in' || tool === 'zoom_out') {
      // Handle zoom
      return;
    }
    setActiveTool(tool);
  };

  return (
    <ProtectedRoute>
      <div className="flex h-screen flex-col">
        <Header />

        <div className="flex flex-1 overflow-hidden">
          {/* Main Content: PDF Viewer */}
          <div className="flex-1 overflow-y-auto bg-white dark:bg-gray-900/50 p-8 relative">
            <div className="max-w-4xl mx-auto">
              <AnnotationToolbar onToolSelect={handleToolSelect} />
              <PDFViewer title="The Future of Artificial Intelligence" />
            </div>
          </div>

          {/* Right Sidebar: Annotations */}
          <AnnotationSidebar
            annotations={annotations}
            paperTitle="The Future of AI"
          />
        </div>
      </div>
    </ProtectedRoute>
  );
}
