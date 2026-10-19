# Battman cards

Battman cards are dashboard cards you can put on any view, on any dashboard, and
that update with Battman releases. Each one is a plain YAML card file.

## Using one

Edit dashboard → **Add card** → search **Battman** → pick one (each has a live
preview). On the dashboard its YAML is just:

```yaml
type: custom:battman-limits
```

Copy and paste it anywhere like any card. Every copy updates when Battman does.

**Make one copy your own:** open the card's editor → **Convert to plain YAML**. You
get the full card YAML with your entities filled in; that copy stops updating.

| Card | What it shows | Needs |
|---|---|---|
| `battman-limits` | Grid export, PV max and max charge limits; tap one to change it | button-card, card-mod |

## How a card is made

`custom_components/battman/cards/<id>.yaml` is ordinary card YAML, exactly what
you'd paste onto a view, with a two-line header:

```yaml
# name: Limits
# description: Grid export, PV max and max charge limits. Tap one to change it.
type: vertical-stack
cards:
  - type: custom:button-card
    entity: '[[map:grid_export_limit]]'
    ...
```

`[[map:name]]` is an entry in Battman's entity map (Battman → Configure). Quote it
when it's a whole value, as above. HA's own `{{ … }}` templates are left alone.

## Trying out changes on your own HA

1. Copy the card file to `config/battman/cards/<id>.yaml` (same name).
2. Edit that copy. On this HA it's used instead of Battman's, everywhere the card is.
3. Refresh the page to see the change.
4. While any file is in that folder, a **Repair** lists them, so a local copy is
   never forgotten.
5. When it's right, the file goes into the Battman repo (`custom_components/battman/cards/`)
   and out in the next release. Then delete your local copy.

A new file in that folder (a name Battman doesn't ship) is a new card of your own:
`custom:battman-<name>`, after restarting HA.

Problems show on the card itself: an unknown card, YAML that doesn't parse, a map
entry that doesn't exist, or a card type that isn't installed.
