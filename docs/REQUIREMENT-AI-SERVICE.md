# 模块需求文档 — AI 服务

## 1. 模块概述

**技术栈**: Python 3.12 + FastAPI + LangChain + OpenAI API + pgvector

**职责**: 独立的 AI 推理微服务，提供聊天、推荐、内容生成功能

**部署**: K3s Pod，2 replicas，ClusterIP:8001

---

## 2. 服务架构

```
ai-service/
├── src/ai_service/
│   ├── main.py              # FastAPI 应用入口
│   ├── chat.py              # AI 聊天服务
│   ├── rag.py               # RAG 管道
│   ├── recommendation.py    # 推荐引擎
│   ├── content_gen.py       # 内容生成
│   ├── embedding.py         # Embedding 服务
│   ├── models.py            # AI 领域模型
│   └── config.py            # 配置管理
├── tests/
│   ├── test_chat.py
│   ├── test_rag.py
│   └── test_recommendation.py
└── Dockerfile
```

---

## 3. AI 聊天服务

### 3.1 系统 Prompt 设计

```python
SYSTEM_PROMPT = """
You are Forge Assistant, a knowledgeable and caring pet care expert.

User Information:
- Pet Name: {pet_name}
- Breed: {breed}
- Age Stage: {life_stage}
- Weight: {weight} kg
- Allergies: {allergies}
- Health Notes: {health_notes}

Product Catalog Context:
{product_context}

Knowledge Retrieval:
{retrieved_context}

Guidelines:
1. Always consider the pet's specific needs (breed, age, allergies)
2. Recommend products naturally within your responses
3. Be warm, empathetic, and professional
4. If unsure about medical advice, recommend consulting a vet
5. Product recommendations should be relevant and justified
6. Use markdown formatting for readability
7. Keep responses concise (under 300 words)
8. When recommending products, include product_id for the frontend

Product Recommendation Format:
When suggesting a product, use this pattern:
"I recommend [{product_name}]({product_id}) because [reason]"
"""
```

### 3.2 聊天 API

```python
@app.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    ws: WebSocket = None,
):
    """
    AI 聊天 (SSE 流式响应)
    
    Request:
    {
        "message": "What food is good for my golden retriever?",
        "conversation_id": "uuid",
        "pet_id": "uuid"
    }
    
    Response: SSE stream
    """
    user_id = get_current_user(ws).id
    
    # 获取宠物信息
    pet_info = await get_pet_info(request.pet_id) if request.pet_id else None
    
    # 获取历史对话
    history = await get_conversation_history(request.conversation_id, user_id)
    
    # RAG 检索
    retrieved = await rag_pipeline.retrieve(request.message, k=5)
    
    # 构建 Prompt
    messages = build_messages(
        system_prompt=SYSTEM_PROMPT.format(
            pet_name=pet_info.name if pet_info else "Unknown",
            breed=pet_info.breed.value if pet_info else "Unknown",
            life_stage=pet_info.lifecycle.value if pet_info else "Unknown",
            weight=pet_info.weight or "Unknown",
            allergies=", ".join(pet_info.allergies) if pet_info else "None",
            health_notes=", ".join(pet_info.health_notes) if pet_info else "None",
            product_context=get_product_context(),
            retrieved_context="\n".join(c.content for c in retrieved),
        ),
        user_message=request.message,
        history=history,
    )
    
    # 流式生成
    async def event_generator():
        full_response = ""
        recommendations = []
        
        async for chunk in openai_client.stream_chat(messages):
            full_response += chunk
            # 提取推荐商品
            recs = extract_recommendations(chunk, retrieved)
            if recs:
                recommendations.extend(recs)
                yield f"data: {{\"recommendations\": {json.dumps(recs)}}}\n\n"
            yield f'data: {{"chunk": {json.dumps(chunk)}}}\n\n'
        
        # 保存对话
        await save_conversation(
            user_id=user_id,
            message=request.message,
            response=full_response,
            recommendations=recommendations,
            conversation_id=request.conversation_id,
        )
        
        yield f'data: {{"done": true, "recommendations": {json.dumps(recommendations)}}}\n\n'
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
```

### 3.3 WebSocket 支持

```python
@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket 实时聊天"""
    await websocket.accept()
    
    user_id = validate_ws_token(websocket)
    
    async with chat_manager.connect(user_id) as room:
        async for message in room:
            if message.type == "message":
                # 处理用户消息
                response = await process_chat_message(
                    user_id=user_id,
                    content=message.content,
                    pet_id=message.pet_id,
                )
                
                # 流式发送
                for chunk in response.chunks:
                    await websocket.send_json({
                        "type": "chunk",
                        "content": chunk.text,
                    })
                
                # 发送推荐
                if response.recommendations:
                    await websocket.send_json({
                        "type": "recommendations",
                        "items": response.recommendations,
                    })
                
                # 发送结束信号
                await websocket.send_json({"type": "done"})
```

---

## 4. RAG 管道

### 4.1 文档分块

```python
class RAGPipeline:
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 50
    
    def chunk_document(self, text: str) -> list[str]:
        """将文档分割为重叠的文本块"""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.CHUNK_SIZE,
            chunk_overlap=self.CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        return splitter.split_text(text)
    
    def embed_chunks(self, texts: list[str]) -> list[list[float]]:
        """批量生成 embedding"""
        response = openai_client.create_embeddings(
            model="text-embedding-3-small",
            input=texts,
            dimensions=1536,
        )
        return [item.embedding for item in response.data]
```

### 4.2 向量检索

```python
class VectorStore:
    """pgvector 向量存储"""
    
    async def upsert(self, product_id: UUID, embedding: list[float], metadata: dict):
        """插入或更新向量"""
        await self.conn.execute(
            """INSERT INTO product_embeddings 
               (product_id, embedding, metadata) 
               VALUES ($1, $2, $3)
               ON CONFLICT (product_id) DO UPDATE 
               SET embedding = EXCLUDED.embedding,
                   metadata = EXCLUDED.metadata""",
            product_id, embedding, json.dumps(metadata),
        )
    
    async def similarity_search(
        self, query_embedding: list[float], k: int = 5
    ) -> list[dict]:
        """余弦相似度搜索"""
        result = await self.conn.fetch(
            """SELECT 
                 product_id, 
                 1 - (embedding <=> $1::vector) as similarity,
                 metadata
               FROM product_embeddings
               WHERE 1 - (embedding <=> $1::vector) > 0.3
               ORDER BY similarity DESC 
               LIMIT $2""",
            np.array(query_embedding).tolist(),
            k,
        )
        return [
            {
                "product_id": row["product_id"],
                "similarity": float(row["similarity"]),
                "metadata": row["metadata"],
            }
            for row in result
        ]
    
    async def retrieve_context(
        self, query: str, k: int = 5
    ) -> list[RetrievedContext]:
        """检索相关上下文"""
        query_embedding = await self.embed_query(query)
        results = await self.similarity_search(query_embedding, k)
        
        return [
            RetrievedContext(
                product_id=r["product_id"],
                content=r["metadata"]["description"],
                similarity=r["similarity"],
            )
            for r in results
        ]
```

### 4.3 文档入库

```python
@app.on_event("startup")
async def ingest_documents():
    """启动时索引商品文档"""
    products = await product_repo.list_all()
    
    for product in products:
        # 生成产品描述文本
        text = f"""
        Product: {product.name}
        Category: {product.category.value}
        Description: {product.ai_description or product.description}
        Suitable for: {', '.join(product.suitable_for.get('life_stages', []))}
        Breed groups: {', '.join(product.breed_groups)}
        Tags: {', '.join(product.tags)}
        """
        
        # 分块 + Embedding
        chunks = rag.chunk_document(text)
        embeddings = rag.embed_chunks(chunks)
        
        # 存入 pgvector
        for chunk, embedding in zip(chunks, embeddings):
            await vector_store.upsert(
                product_id=product.id,
                embedding=embedding,
                metadata={
                    "name": product.name,
                    "description": chunk,
                    "category": product.category.value,
                    "price": float(product.price),
                },
            )
```

---

## 5. 推荐引擎

### 5.1 混合推荐

```python
class RecommendationEngine:
    async def recommend(
        self,
        user_id: UUID,
        pet_id: UUID | None = None,
        limit: int = 10,
    ) -> list[Product]:
        sources = []
        
        # 1. 基于宠物档案 (40%)
        if pet_id:
            pet = await pet_repo.get_by_id(pet_id)
            pet_recs = await self._recommend_by_pet_profile(pet, limit=20)
            sources.append(("pet_profile", pet_recs, 0.4))
        
        # 2. 协同过滤 (30%)
        cf_recs = await self._collaborative_filtering(user_id, limit=20)
        sources.append(("collaborative", cf_recs, 0.3))
        
        # 3. 季节性 (30%)
        seasonal = await self._seasonal_recommendation(limit=20)
        sources.append(("seasonal", seasonal, 0.3))
        
        # 加权合并
        return self._rank_combined(sources, limit)
    
    async def _recommend_by_pet_profile(
        self, pet: PetProfile, limit: int
    ) -> list[Product]:
        """基于宠物档案推荐"""
        # 1. 找到适合的品类和条件
        suitable_categories = self._get_suitable_categories(pet)
        suitable_conditions = self._get_suitable_conditions(pet)
        
        # 2. 排除过敏原相关商品
        excluded_tags = [f"contains_{a}" for a in pet.allergies]
        
        # 3. 查询商品
        products = await product_repo.filter(
            categories=suitable_categories,
            conditions=suitable_conditions,
            exclude_tags=excluded_tags,
            limit=limit * 2,
        )
        
        # 4. 按匹配度排序
        return sorted(products, key=lambda p: self._match_score(pet, p), reverse=True)[:limit]
    
    async def _collaborative_filtering(
        self, user_id: UUID, limit: int
    ) -> list[Product]:
        """基于用户行为的协同过滤"""
        # 1. 找到相似用户
        similar_users = await self._find_similar_users(user_id)
        
        # 2. 获取这些用户购买的商品
        purchased = await order_repo.get_products_by_users(similar_users)
        
        # 3. 排除当前用户已购买的
        user_purchased = await order_repo.get_user_product_ids(user_id)
        
        # 4. 按购买频次排序
        return sorted(
            [p for p in purchased if p.id not in user_purchased],
            key=lambda p: p.purchase_count,
            reverse=True,
        )[:limit]
```

---

## 6. 内容生成

### 6.1 产品描述生成

```python
class ContentGenerator:
    async def generate_product_description(
        self,
        product: Product,
        locale: str = "en",
    ) -> str:
        """生成 SEO 优化的产品描述"""
        prompt = f"""
        Write a compelling, SEO-optimized product description for:

        Product: {product.name}
        Category: {product.category.value}
        Target: {', '.join(product.breed_groups)}
        Features: {', '.join(product.tags)}
        Benefits: {product.suitable_for.get('conditions', [])}

        Requirements:
        - 150-250 words
        - Include keywords naturally
        - Highlight key benefits
        - Mention suitable pet types
        - SEO-friendly structure
        """
        
        response = await openai_client.chat(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-4o",
            temperature=0.7,
        )
        
        return response.choices[0].message.content
```

### 6.2 批量内容生成

```python
@app.on_event("startup")
async def generate_content_for_new_products():
    """定时扫描新商品并生成描述"""
    while True:
        pending = await product_repo.get_pending_ai_content()
        
        for product in pending:
            try:
                description = await content_gen.generate_product_description(product)
                await product_repo.update_ai_content(
                    product_id=product.id,
                    description=description,
                )
                logger.info("Generated content for product %s", product.id)
            except Exception:
                logger.exception("Failed to generate content for %s", product.id)
        
        await asyncio.sleep(3600)  # 每小时检查一次
```

---

## 7. 配置

```python
# ai-service/src/ai_service/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str
    openai_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    
    postgres_url: str
    redis_url: str
    
    rag_top_k: int = 5
    rag_similarity_threshold: float = 0.3
    
    rate_limit_per_minute: int = 30
    
    class Config:
        env_prefix = "AI_"
```
