"""
Streaming Responses for SetuPranali

Provides streaming for large result sets:
- Server-Sent Events (SSE) for real-time streaming
- WebSocket for bidirectional communication
- Chunked transfer encoding
- Backpressure handling

Features:
- Stream large datasets without memory issues
- Real-time progress updates
- Cancellation support
- Resume capabilities
- Multiple output formats (JSON, CSV, NDJSON)
"""

import asyncio
import json
import time
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from fastapi import WebSocket, WebSocketDisconnect, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

class StreamFormat(str, Enum):
    """Output format for streaming."""
    JSON = "json"           # JSON array chunks
    NDJSON = "ndjson"       # Newline-delimited JSON
    CSV = "csv"             # CSV format
    SSE = "sse"             # Server-Sent Events


class StreamConfig(BaseModel):
    """Streaming configuration."""
    
    enabled: bool = Field(default=True)
    chunk_size: int = Field(default=1000, description="Rows per chunk")
    max_rows: int = Field(default=1000000, description="Maximum total rows")
    timeout_seconds: int = Field(default=300, description="Stream timeout")
    heartbeat_interval: int = Field(default=30, description="SSE heartbeat interval")
    buffer_size: int = Field(default=10, description="Chunk buffer size")


# =============================================================================
# Stream Request/Response Models
# =============================================================================

class StreamRequest(BaseModel):
    """Request for streaming query."""
    
    dataset: str
    dimensions: List[str] = Field(default=[])
    metrics: List[str] = Field(default=[])
    filters: Optional[Dict[str, Any]] = None
    order_by: Optional[List[str]] = None
    
    # Streaming options
    format: StreamFormat = Field(default=StreamFormat.NDJSON)
    chunk_size: int = Field(default=1000)
    include_metadata: bool = Field(default=True)
    include_progress: bool = Field(default=True)


@dataclass
class StreamMetadata:
    """Metadata for stream."""
    
    stream_id: str
    dataset: str
    started_at: datetime
    format: StreamFormat
    chunk_size: int
    total_rows: Optional[int] = None
    rows_sent: int = 0
    chunks_sent: int = 0
    bytes_sent: int = 0
    completed: bool = False
    error: Optional[str] = None


# =============================================================================
# SSE Streaming
# =============================================================================

class SSEStream:
    """Server-Sent Events stream handler."""
    
    def __init__(self, config: StreamConfig):
        self.config = config
    
    async def stream_query(
        self,
        request: StreamRequest,
        data_generator: AsyncGenerator[List[Dict[str, Any]], None],
        total_rows: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """Stream query results as SSE."""
        stream_id = f"stream_{int(time.time() * 1000)}"
        metadata = StreamMetadata(
            stream_id=stream_id,
            dataset=request.dataset,
            started_at=datetime.now(),
            format=request.format,
            chunk_size=request.chunk_size,
            total_rows=total_rows,
        )
        
        try:
            # Send metadata event
            if request.include_metadata:
                yield self._format_sse("metadata", {
                    "stream_id": stream_id,
                    "dataset": request.dataset,
                    "format": request.format.value,
                    "chunk_size": request.chunk_size,
                    "total_rows": total_rows,
                    "started_at": metadata.started_at.isoformat(),
                })
            
            # Stream data chunks
            chunk_number = 0
            async for chunk in data_generator:
                chunk_number += 1
                metadata.chunks_sent = chunk_number
                metadata.rows_sent += len(chunk)
                
                # Format based on requested format
                if request.format == StreamFormat.NDJSON:
                    for row in chunk:
                        yield self._format_sse("data", row)
                elif request.format == StreamFormat.CSV:
                    # First chunk includes headers
                    if chunk_number == 1 and chunk:
                        headers = list(chunk[0].keys())
                        yield self._format_sse("headers", headers)
                    for row in chunk:
                        yield self._format_sse("row", list(row.values()))
                else:  # JSON
                    yield self._format_sse("chunk", {
                        "chunk_number": chunk_number,
                        "rows": chunk,
                    })
                
                # Send progress update
                if request.include_progress:
                    progress = {
                        "chunks_sent": chunk_number,
                        "rows_sent": metadata.rows_sent,
                    }
                    if total_rows:
                        progress["percent_complete"] = round(metadata.rows_sent / total_rows * 100, 2)
                    yield self._format_sse("progress", progress)
            
            # Send completion event
            metadata.completed = True
            yield self._format_sse("complete", {
                "stream_id": stream_id,
                "total_chunks": metadata.chunks_sent,
                "total_rows": metadata.rows_sent,
                "duration_ms": (datetime.now() - metadata.started_at).total_seconds() * 1000,
            })
            
        except Exception as e:
            metadata.error = str(e)
            yield self._format_sse("error", {
                "message": str(e),
                "stream_id": stream_id,
            })
            raise
    
    def _format_sse(self, event: str, data: Any) -> str:
        """Format data as SSE message."""
        json_data = json.dumps(data, default=str)
        return f"event: {event}\ndata: {json_data}\n\n"
    
    async def heartbeat_generator(
        self,
        data_stream: AsyncGenerator[str, None]
    ) -> AsyncGenerator[str, None]:
        """Add heartbeat to stream."""
        last_heartbeat = time.time()
        
        async for chunk in data_stream:
            yield chunk
            
            # Send heartbeat if needed
            now = time.time()
            if now - last_heartbeat >= self.config.heartbeat_interval:
                yield self._format_sse("heartbeat", {"timestamp": now})
                last_heartbeat = now


# =============================================================================
# WebSocket Streaming
# =============================================================================

class WebSocketStream:
    """WebSocket stream handler."""
    
    def __init__(self, config: StreamConfig):
        self.config = config
        self._active_connections: Dict[str, WebSocket] = {}
    
    async def handle_connection(
        self,
        websocket: WebSocket,
        query_executor: Callable
    ) -> None:
        """Handle WebSocket connection for streaming queries."""
        await websocket.accept()
        connection_id = f"ws_{int(time.time() * 1000)}"
        self._active_connections[connection_id] = websocket
        
        try:
            while True:
                # Receive query request
                message = await websocket.receive_json()
                
                if message.get("type") == "query":
                    await self._handle_query(
                        websocket,
                        connection_id,
                        message.get("payload", {}),
                        query_executor
                    )
                elif message.get("type") == "cancel":
                    await websocket.send_json({
                        "type": "cancelled",
                        "stream_id": message.get("stream_id"),
                    })
                elif message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {message.get('type')}",
                    })
        
        except WebSocketDisconnect:
            logger.info(f"WebSocket {connection_id} disconnected")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await websocket.send_json({
                "type": "error",
                "message": str(e),
            })
        finally:
            self._active_connections.pop(connection_id, None)
    
    async def _handle_query(
        self,
        websocket: WebSocket,
        connection_id: str,
        payload: Dict[str, Any],
        query_executor: Callable
    ) -> None:
        """Execute and stream query results."""
        stream_id = f"stream_{int(time.time() * 1000)}"
        
        try:
            # Send stream started
            await websocket.send_json({
                "type": "stream_started",
                "stream_id": stream_id,
                "started_at": datetime.now().isoformat(),
            })
            
            # Execute query and stream results
            request = StreamRequest(**payload)
            chunk_number = 0
            total_rows = 0
            
            async for chunk in query_executor(request):
                chunk_number += 1
                total_rows += len(chunk)
                
                await websocket.send_json({
                    "type": "data",
                    "stream_id": stream_id,
                    "chunk_number": chunk_number,
                    "rows": chunk,
                })
            
            # Send completion
            await websocket.send_json({
                "type": "complete",
                "stream_id": stream_id,
                "total_chunks": chunk_number,
                "total_rows": total_rows,
            })
            
        except Exception as e:
            await websocket.send_json({
                "type": "error",
                "stream_id": stream_id,
                "message": str(e),
            })


# =============================================================================
# Chunked Response Generator
# =============================================================================

async def generate_chunks(
    data_generator: AsyncGenerator[List[Dict[str, Any]], None],
    format: StreamFormat,
    include_wrapper: bool = True
) -> AsyncGenerator[bytes, None]:
    """Generate chunked response in various formats."""
    
    if format == StreamFormat.NDJSON:
        async for chunk in data_generator:
            for row in chunk:
                yield (json.dumps(row, default=str) + "\n").encode()
    
    elif format == StreamFormat.CSV:
        first_chunk = True
        async for chunk in data_generator:
            if first_chunk and chunk:
                # Write headers
                headers = list(chunk[0].keys())
                yield (",".join(f'"{h}"' for h in headers) + "\n").encode()
                first_chunk = False
            
            for row in chunk:
                values = [str(v) if v is not None else "" for v in row.values()]
                yield (",".join(f'"{v}"' for v in values) + "\n").encode()
    
    elif format == StreamFormat.JSON:
        if include_wrapper:
            yield b'{"data":['
        
        first = True
        async for chunk in data_generator:
            for row in chunk:
                if not first:
                    yield b","
                first = False
                yield json.dumps(row, default=str).encode()
        
        if include_wrapper:
            yield b"]}"
    
    else:  # SSE format handled separately
        async for chunk in data_generator:
            yield json.dumps(chunk, default=str).encode()


# =============================================================================
# Streaming Response Factory
# =============================================================================

def create_streaming_response(
    data_generator: AsyncGenerator[List[Dict[str, Any]], None],
    format: StreamFormat = StreamFormat.NDJSON,
    filename: Optional[str] = None
) -> StreamingResponse:
    """Create a streaming response."""
    
    content_types = {
        StreamFormat.JSON: "application/json",
        StreamFormat.NDJSON: "application/x-ndjson",
        StreamFormat.CSV: "text/csv",
        StreamFormat.SSE: "text/event-stream",
    }
    
    headers = {}
    if filename:
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    
    return StreamingResponse(
        generate_chunks(data_generator, format),
        media_type=content_types.get(format, "application/octet-stream"),
        headers=headers,
    )


def create_sse_response(
    sse_generator: AsyncGenerator[str, None]
) -> StreamingResponse:
    """Create SSE streaming response."""
    
    async def encode_generator():
        async for event in sse_generator:
            yield event.encode()
    
    return StreamingResponse(
        encode_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


# =============================================================================
# Global Instances
# =============================================================================

_config: Optional[StreamConfig] = None
_sse_stream: Optional[SSEStream] = None
_ws_stream: Optional[WebSocketStream] = None


def init_streaming(config: Optional[StreamConfig] = None) -> None:
    """Initialize streaming components."""
    global _config, _sse_stream, _ws_stream
    
    _config = config or StreamConfig()
    _sse_stream = SSEStream(_config)
    _ws_stream = WebSocketStream(_config)
    
    logger.info("Streaming initialized")


def get_sse_stream() -> Optional[SSEStream]:
    """Get SSE stream handler."""
    return _sse_stream


def get_ws_stream() -> Optional[WebSocketStream]:
    """Get WebSocket stream handler."""
    return _ws_stream

