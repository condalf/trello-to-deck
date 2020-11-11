from dataclasses import dataclass
from typing import List
import dateutil.parser

color_map = {
    "green": "49b675",
    "yellow": "FFFF00",
    "orange": "FFA500",
    "red": "FF0000",
    "purple": "800080",
    "blue": "0000FF",
    "sky": "87ceeb",
    "lime": "9efd38",
    "pink": "c09da4",
    "black": "000000",
    None: "b3bac5"
}


@dataclass
class ChecklistItem:
    name: str
    completed: bool
    order: int


@dataclass
class Checklist:
    name: str
    items: List[str]
    order: int


@dataclass
class Label:
    trelloId: str
    name: str
    color: str

@dataclass
class Attachment:
    fileName: str
    url: str
    mimeType: str

@dataclass
class Card:
    name: str
    archived: bool
    due_date: str
    description: str
    order: int  # Order within a stack
    checklists: List[Checklist]
    labels: List[Label]
    trelloUrl: str
    comments: List[str]
    attachments: List[Attachment]

@dataclass
class Stack:
    name: str
    order: int
    cards: List[Card]


@dataclass
class Board:
    title: str
    color: str
    labels: List[Label]
    stacks: Stack

def get_checklist_by_card(checklists, card_id):
    checklists = filter(lambda checklist: checklist.idCard == card_id, checklists)
    return list(
        sorted(
            map(
                lambda checklist: Checklist(
                    checklist.name,
                    list(
                        sorted(
                            map(
                                lambda item: ChecklistItem(
                                    item.name, item.name == "completed", item.pos
                                ),
                                checklist.checkItems,
                            ),
                            key=lambda item: item.order,
                        )
                    ),
                    checklist.pos,
                ),
                checklists,
            ),
            key=lambda checklist: checklist.order,
        )
    )


def get_comments_by_card(actions, trello_card_id):
    commentCardActions = filter(lambda action: action.type == 'commentCard' and action.data.card.id == trello_card_id, actions)
    comments = list(map(lambda action: action.data.text, commentCardActions))
    return comments

def get_label_ids(labels, label_ids):
    return list(filter(lambda label: label.trelloId in label_ids, labels))


def get_cards_by_stack(cards, checklists, actions, labels, trello_stack_id):
    cards = filter(lambda card: card.idList == trello_stack_id, cards)
    return list(
        sorted(
            map(
                lambda card: Card(
                    card.name,
                    card.closed,
                    dateutil.parser.isoparse(card.badges.due)
                    if card.badges.due is not None
                    else None,
                    card.desc,
                    card.pos,
                    get_checklist_by_card(checklists, card.id),
                    get_label_ids(labels, card.idLabels),
                    card.shortUrl,
                    get_comments_by_card(actions, card.id),
                    list(map(lambda attachment: Attachment(attachment.fileName, attachment.url, attachment.mimeType), filter(lambda attachment: attachment.isUpload, card.attachments)))
                ),
                cards,
            ),
            key=lambda card: card.order,
        )
    )


def to_board(trello_json):
    labels = list(
        map(
            lambda tuple: Label(tuple[1].id, tuple[1].name if len(tuple[1].name) > 0 else "Label %d" % (tuple[0] + 1), color_map[tuple[1].color]),
            enumerate(trello_json.labels),
        )
    )

    not_closed_stacks = filter(lambda stack: not stack.closed, trello_json.lists)
    lists = list(
        sorted(
            map(
                lambda stack: Stack(
                    stack.name,
                    stack.pos,
                    get_cards_by_stack(
                        trello_json.cards, trello_json.checklists, trello_json.actions, labels, stack.id
                    ),
                ),
                not_closed_stacks,
            ),
            key=lambda stack: stack.order,
        )
    )

    # If background has 24 chars then it is an images
    try:
        if len(trello_json.prefs.background) != 24:
            background_color = color_map[trello_json.prefs.background] 
        else:
            background_color = "green"
    except KeyError:
        background_color = "green"


    return Board(
        trello_json.name, background_color, labels, lists
    )
