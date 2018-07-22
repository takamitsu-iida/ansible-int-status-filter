# インタフェース状態をチェックするフィルタの例

ある状態を満たすまでタスクを待機する、というのは `until` と `retries` と `delay` を指定すれば実現できます。

```yml
tasks:

  - name: インタフェースが全てupしているか確認
    ios_command:
      commands: "{{ cmds }}"
    register: r

    until: 条件式
    retries: 100  # リトライ回数
    delay: 10  # 秒間隔
```

しかし、untilは1行で書かなければいけないため、フィルタをつなぎ合わせた複雑な条件式になりがちです。

ルータのインタフェース状態をチェックして全てupするまでプレイブックを待機させたいとします。

シスコルータに以下のコマンドを打ち込むと、

```yml
- show interface GigabitEthernet1 | inc line protocol is
- show interface GigabitEthernet2 | inc line protocol is
- show interface GigabitEthernet3 | inc line protocol is
- show interface GigabitEthernet4 | inc line protocol is
```

次のような応答が返ってきますので、これを利用して全てのインタフェースがupしているかを判定するとします。

```yml
- GigabitEthernet1 is up, line protocol is up
- GigabitEthernet2 is up, line protocol is up
- GigabitEthernet3 is up, line protocol is up
- GigabitEthernet4 is up, line protocol is up
```

全てのインタフェースについて `line protocol is` **up** となっていれば条件を満たすことになりますので、その条件判定を1行で記述することになります。

<br><br>

# until式の例・その１

何とか読めなくもない、ギリギリの式がこれ。

regex_replaceを使ってline protocol isの後の **up** だけを取り出して `[up, up, up, up]` のような配列にして、それをjoinで1行の文字列にして、その中に 'down' が含まれていたらダメ、という判定です。

```yml
until: (r.stdout | map('regex_replace', '.* line protocol is (.*)', '\\1') | join(' ')).find('down') == -1
```

<br><br>

# until式の例・その２

配列の中に'down'という文字がないかをチェックする方式です。

この例のuntilの先頭にあるdownは文字列ではなく変数です。したがって、どこか別の場所で定義しておかなければいけません。

面倒です。

```yml
until: down not in r.stdout | map('regex_replace', '.* line protocol is (.*)', '\\1') | list
```

<br><br>

# until式の例・その３

`['up', 'up', 'up', 'up']` のような配列だと `is all` で判定できませんので、'up'なら'True'、'down'なら'False'に置き換えます。それをbool値に変えて、最後に `is all` で判定する方法です。

カオスな条件式です。

```yml
until: r.stdout | map('replace', 'up', true) | map('replace', 'down', false) | map('bool') | list is all
```

<br><br>

# 自分でフィルタを作った場合

コマンドの応答の配列を受け取って、条件を満たせばTrue、満たさなければFalseを返すフィルタを作ってしまえば、until式はここまで簡単にできます。

`intf_status` は自作のフィルタです。

```yml
until: r.stdout | intf_status
```

<br><br>

# ansible.cfg

独自のフィルタを読み込む場所を `filter_plugins` で指定します。

```ini
[defaults]

# filterプラグイン
filter_plugins = ./plugins/filter
```

<br><br>

# プレイブック

プレイブック全体はこのようになります。
ios_commandモジュールを使って cmds 配列のコマンドを打ち込みます。

```yml
---
#
# Ciscoルータのインタフェースの状態を確認して全てupになるまで待機します
#
# 2018/07/15 初版
#
# Takamitsu IIDA (@takamitsu-iida)

- name: 全てのインタフェースの状態がupするまで待機します
  hosts: r1
  gather_facts: False
  strategy: linear  # free
  serial: 0

  vars:
    cmds:
      - show interface GigabitEthernet1 | inc line protocol is
      - show interface GigabitEthernet2 | inc line protocol is
      - show interface GigabitEthernet3 | inc line protocol is
      - show interface GigabitEthernet4 | inc line protocol is


  tasks:

    - name: インタフェースが全てupしているか確認
      ios_command:
        commands: "{{ cmds }}"
      register: r
      until: r.stdout | intf_status
      retries: 100
      delay: 10

    - name: 結果表示
      when: r is success
      debug: msg="全てのインタフェースがupになっていることを確認しました"
```

<br><br>

# 実行結果

プレイブックを実行すると、条件を満たしていないため同じ処理を繰り返します。

```bash
iida-macbook-pro:ansible-int-status-filter iida$ ansible-playbook cisco_watch_int.yml

PLAY [インタフェースの状態がupするまで待機します] *********************************************************************************************

TASK [インタフェースが全てupしているか確認] ************************************************************************************************
FAILED - RETRYING: インタフェースが全てupしているか確認 (100 retries left).
FAILED - RETRYING: インタフェースが全てupしているか確認 (99 retries left).
FAILED - RETRYING: インタフェースが全てupしているか確認 (98 retries left).
FAILED - RETRYING: インタフェースが全てupしているか確認 (97 retries left).
FAILED - RETRYING: インタフェースが全てupしているか確認 (96 retries left).
ok: [r1]

TASK [結果表示] ***************************************************************************************************************
ok: [r1] => {}

MSG:

全てのインタフェースがupになっていることを確認しました


PLAY RECAP ****************************************************************************************************************
r1                         : ok=2    changed=0    unreachable=0    failed=0

iida-macbook-pro:ansible-int-status-filter iida$
```

別のターミナルからSSHでルータに乗り込み、手作業で以下のコマンドを打ち込みました。

```none
csr#show int | inc line protocol
GigabitEthernet1 is up, line protocol is up
GigabitEthernet2 is up, line protocol is up
GigabitEthernet3 is administratively down, line protocol is down
GigabitEthernet4 is administratively down, line protocol is down
csr#conf t
Enter configuration commands, one per line.  End with CNTL/Z.
csr(config)#int gig 3
csr(config-if)#no shut
csr(config-if)#int gig 4
csr(config-if)#no shut
csr(config-if)#
```

その結果全てのインタフェースが`up`状態になりプレイブックは完了しています。

<br><br>

# 独自フィルタ

フィルタはPythonで作成します。一つのファイルに何個でもフィルタを定義できます。

```python
import re

from ansible.module_utils.six import string_types
from ansible.errors import AnsibleFilterError

try:
  from __main__ import display
except ImportError:
  from ansible.utils.display import Display
  display = Display()


def intf_status(stdout):

  if isinstance(stdout, string_types):
    stdout = list(stdout)

  if not isinstance(stdout, list):
    raise AnsibleFilterError("filter input should be a list of string, but was given a input of %s" % (type(stdout)))

  updown_list = []

  for s in stdout:
    if not isinstance(s, string_types):
      raise AnsibleFilterError("filter input should be a string, but was given a input of %s" % (type(s)))

    match = re.match(r'.* line protocol is (.*)', s)
    if match:
      updown_list.append(match.group(1) == "up")
    else:
      raise AnsibleFilterError("failed to parse interface status, %s" % s)

  if not updown_list:
    AnsibleFilterError("unknown interface status")

  display.vvvv("intf_status updown_list: %s " % ' '.join([str(x) for x in updown_list]))

  return all(updown_list)


# ---- Ansible filters ----

class FilterModule(object):
  """Filters for working with output from network devices
  """

  filter_map = {
    'intf_status': intf_status,
  }

  def filters(self):
    return self.filter_map

```

line protocol is の後が **up** ならTrue、それ以外はFalseを格納した配列を作り、最後にall()で判定しています。
