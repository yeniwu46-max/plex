"""驿站回复质量：明确概念题不应被低质反问糊弄。"""
from app.services.messenger_chat import MessengerChatService


def test_evasive_reply_detected_for_clear_question():
    reply = '你好！看起来你在学习Python编程，但似乎有些困惑。能否告诉我你具体遇到了什么问题呢？'
    assert MessengerChatService._is_evasive_reply(reply, '请解释列表推导式并给例子')


def test_substantive_reply_not_evasive():
    reply = (
        '**列表推导式**用一行表达式生成列表。'
        '例如：`[x*x for x in range(5)]` 得到平方数。'
        '思考：如果加 `if x % 2 == 0`，结果会变成什么？'
    )
    assert not MessengerChatService._is_evasive_reply(reply, '请解释列表推导式并给例子')


def test_vague_student_message_allows_clarifying_question():
    reply = '你卡在报错信息的哪一行？把那一行贴过来我帮你看。'
    assert not MessengerChatService._is_evasive_reply(reply, '不会')


def test_off_topic_reply_rejected():
    reply = '变量用来保存数据，例如 `my_variable = 10`。'
    assert MessengerChatService._is_off_topic_reply(reply, '请解释列表推导式并给例子')


def test_on_topic_reply_accepted():
    reply = '列表推导式可以用 `[x*x for x in range(5)]` 一行生成平方列表。'
    assert not MessengerChatService._is_low_quality_reply(reply, '请解释列表推导式并给例子')
