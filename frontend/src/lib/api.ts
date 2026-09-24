import type {
  UploadResponse,
  AnalysisResponse,
  QAResponse,
  RedlineResponse,
} from '../types';

const BASE_URL = '/api';

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.text();
    throw new ApiError(
      body || `HTTP ${response.status}: ${response.statusText}`,
      response.status
    );
  }
  return response.json();
}

export async function uploadDocument(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${BASE_URL}/documents`, {
    method: 'POST',
    body: formData,
  });

  return handleResponse<UploadResponse>(response);
}

export async function analyzeDocument(
  documentId: string
): Promise<AnalysisResponse> {
  const response = await fetch(`${BASE_URL}/documents/${documentId}/analyze`, {
    method: 'POST',
  });

  return handleResponse<AnalysisResponse>(response);
}

export async function askQuestion(
  documentId: string,
  question: string
): Promise<QAResponse> {
  const response = await fetch(`${BASE_URL}/documents/${documentId}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });

  return handleResponse<QAResponse>(response);
}

export async function generateRedlines(
  documentId: string
): Promise<RedlineResponse> {
  const response = await fetch(
    `${BASE_URL}/documents/${documentId}/redline`,
    { method: 'POST' }
  );

  return handleResponse<RedlineResponse>(response);
}

export function getBriefPdfUrl(documentId: string): string {
  return `${BASE_URL}/documents/${documentId}/brief.pdf`;
}

export async function healthCheck(): Promise<{ status: string; mock_mode: boolean }> {
  const response = await fetch(`${BASE_URL}/health`);
  return handleResponse(response);
}
